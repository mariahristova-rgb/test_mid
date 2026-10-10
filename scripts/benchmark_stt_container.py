"""Real CPU STT on explicitly generated synthetic telephone-band audio; not human speech acceptance."""
from datetime import datetime,timezone
import io
import json
from pathlib import Path
import time
import wave
import os
import av
import numpy as np
from backend.assistant.local_speech import resample_pcm
from backend.assistant.audio import pcm_16khz,pcm_to_mulaw,mulaw_to_pcm
import httpx

def main():
    directory=Path('/tmp/voice-audio')
    secret=Path('/run/secrets/speech_key').read_text().strip()
    results=[]
    for locale in ('bg-BG','en-US'):
        for phrase in ('request','name','confirm'):
            with wave.open(str(directory/(locale+'-'+phrase+'.wav')),'rb') as wav:
                rate=wav.getframerate(); pcm=wav.readframes(rate*30)
            frame=av.AudioFrame.from_ndarray(np.frombuffer(pcm,dtype='<i2').reshape(1,-1),format='s16',layout='mono')
            frame.sample_rate=rate
            resampler=av.AudioResampler(format='s16',layout='mono',rate=8000)
            converted=[*resampler.resample(frame),*resampler.resample(None)]
            narrow=b''.join(chunk.to_ndarray().tobytes() for chunk in converted)
            telephone=mulaw_to_pcm(pcm_to_mulaw(narrow))
            input_pcm=pcm_16khz(telephone,8000)
            started=time.monotonic()
            response=httpx.post('http://127.0.0.1:8000/transcribe',params={'locale':locale},content=input_pcm,
                headers={'Authorization':'Bearer '+secret},timeout=60,trust_env=False)
            item={'locale':locale,'phrase':phrase,'audio_seconds':len(input_pcm)/32000,'http_status':response.status_code,
                'wall_ms':(time.monotonic()-started)*1000,'resampling':'FFMPEG_BANDLIMITED_8KHZ_MULAW',
                'source':os.environ.get('TEST_AUDIO_SOURCE','ESPEAK_SYNTHETIC_TELEPHONE_BAND'),'actual_response':response.json()}
            results.append(item); print(json.dumps(item,ensure_ascii=False),flush=True)
    report={'timestamp':datetime.now(timezone.utc).isoformat(),'model':'multilingual-small','device':'cpu','compute_type':'int8',
        'beam_size':1,'results':results,'human_speech_validation':'NOT_RUN'}
    Path('/tmp/stt-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__': main()
