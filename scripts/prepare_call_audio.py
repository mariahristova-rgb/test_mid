"""Run inside the owned backend: real local TTS generates synthetic caller fixtures."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import time
import wave
import httpx
from backend.assistant.audio import mulaw_to_pcm


def main():
    out=Path('/tmp/call-input'); out.mkdir(exist_ok=True)
    secret=Path('/run/secrets/speech_key').read_text().strip()
    cases=[('bg-BG','request','Здравейте, искам да запиша час за следващия понеделник в петнадесет часа.'),
        ('bg-BG','request-late','Здравейте, искам да запиша час за следващия понеделник в шестнадесет часа.'),
        ('bg-BG','name','Казвам се Мария Демо.'),('bg-BG','confirm','Потвърждавам часа.'),
        ('en-US','request','Hello, I would like to book a dental checkup next Monday at three PM.'),
        ('en-US','name','My name is Jane Smith.'),('en-US','confirm','Yes, confirm.')]
    results=[]
    with httpx.Client(timeout=70,trust_env=False) as client:
        for locale,phrase,text in cases:
            start=time.monotonic(); first=None; chunks=[]
            with client.stream('POST','http://172.30.7.5:8000/synthesize',params={'locale':locale},
                    headers={'Authorization':'Bearer '+secret},json={'text':text,'voice':'bgtts-bg' if locale=='bg-BG' else 'bgtts-en'}) as response:
                response.raise_for_status()
                if response.headers.get('x-audio-encoding')!='mulaw': raise RuntimeError('Unexpected encoding')
                for chunk in response.iter_bytes():
                    if first is None and chunk: first=(time.monotonic()-start)*1000
                    chunks.append(chunk)
            audio=b''.join(chunks)
            if not audio or len(audio)>60*8000: raise RuntimeError('Invalid generated fixture')
            target=out/f'{locale}-{phrase}.wav'
            with wave.open(str(target),'wb') as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(8000)
                wav.writeframes(mulaw_to_pcm(audio)+b'\x00'*(2*8000*2))
            results.append(dict(locale=locale,phrase=phrase,text=text,first_audio_http_ms=first,
                total_http_ms=(time.monotonic()-start)*1000,speech_seconds=len(audio)/8000,
                trailing_silence_seconds=2,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                state='SYNTHETIC_CPU_AUDIO_NOT_HUMAN_ACCEPTANCE'))
            print(json.dumps(results[-1],ensure_ascii=False),flush=True)
    (out/'synthesis-results.json').write_text(json.dumps({'timestamp':datetime.now(timezone.utc).isoformat(),
        'first_audio_definition':'first response-body audio bytes; batch service, not streaming vocoder',
        'results':results},ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__': main()
