"""One isolated local speech worker per service; models preload before health is ready."""
import hmac
import json
import os
from pathlib import Path
from time import monotonic
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from .domain import DomainError, LOCALES

key=Path(os.environ['SPEECH_KEY_FILE']).read_text().strip()
kind=os.environ['SPEECH_KIND']
if kind=='stt':
    from .local_speech import FasterWhisperProvider
    config=json.loads(Path(os.environ['STT_CONFIG']).read_text())
    engine=FasterWhisperProvider(config['root'],config['manifest'],config['sha256'],device='cpu',compute_type='int8',vad_filter=True,
        chunk_seconds=8,cpu_threads=int(os.getenv('STT_CPU_THREADS','2')), timeout=40, vocabulary=config.get('vocabulary',{}))
elif kind=='tts':
    if os.getenv('LOCAL_TTS_KIND')=='bgtts38':
        from .neural_voice import BG38Voice
        engine=BG38Voice('/models')
    else:
        from .espeak import EspeakProvider
        engine=EspeakProvider()
else: raise RuntimeError('Unsupported explicit speech worker')
app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)


async def bounded_body(request, limit):
    body=bytearray()
    async for chunk in request.stream():
        if len(body)+len(chunk)>limit: raise DomainError('invalid_input',413)
        body.extend(chunk)
    return bytes(body)

@app.get('/health')
def health(): return {'status':'ready','kind':kind,'locales':list(LOCALES),'state':'LIVE_UNVERIFIED'}

@app.middleware('http')
async def authenticate(request:Request,call_next):
    if request.url.path!='/health':
        token=request.headers.get('authorization','').removeprefix('Bearer ')
        if not token or not hmac.compare_digest(token.encode(),key.encode()): return JSONResponse({'code':'unauthorized'},status_code=401)
        try: length=int(request.headers.get('content-length','0'))
        except ValueError: return JSONResponse({'code':'invalid_input'},status_code=422)
        if length>1_000_000: return JSONResponse({'code':'invalid_input'},status_code=413)
    return await call_next(request)

@app.exception_handler(DomainError)
async def error(request,exc): return JSONResponse({'code':exc.code},status_code=exc.status)

@app.post('/transcribe')
async def transcribe(request:Request,locale:str):
    if kind!='stt' or locale not in (*LOCALES,'auto'): raise DomainError('unsupported_locale',422)
    pcm=await bounded_body(request,960000)
    if len(pcm)>960000: raise DomainError('unsupported_audio',413)
    import asyncio
    start=monotonic()
    text=await asyncio.to_thread(engine.transcribe,pcm,None if locale=='auto' else locale)
    return {'text':text,'locale':locale,'elapsed_ms':(monotonic()-start)*1000,'state':'LIVE_UNVERIFIED'}

@app.post('/synthesize')
async def synthesize(request:Request,locale:str):
    if kind!='tts' or locale not in LOCALES: raise DomainError('unsupported_locale',422)
    try: data=json.loads(await bounded_body(request,16000))
    except (ValueError,UnicodeDecodeError): raise DomainError('invalid_input',422) from None
    if not isinstance(data,dict) or set(data)!={'text','voice'} or not isinstance(data['text'],str): raise DomainError('invalid_input',422)
    import asyncio
    audio=await asyncio.to_thread(engine.synthesize,data['text'],locale,data['voice'])
    return Response(audio,media_type='application/octet-stream',headers={'X-Audio-Encoding':'mulaw','X-Sample-Rate':'8000'})
