"""Inside STT container: real known-bg recognition of alternative synthetic Windows audio."""
import json
from pathlib import Path
import time
import wave
import httpx
import av
import numpy as np
from backend.assistant.audio import pcm_to_mulaw,mulaw_to_pcm,pcm_16khz


def main():
    key=Path('/run/secrets/speech_key').read_text().strip(); results=[]
    for source in sorted(Path('/tmp/phase8-windows-voice').glob('*.wav')):
        with wave.open(str(source)) as wav:
            rate=wav.getframerate(); channels=wav.getnchannels(); width=wav.getsampwidth(); pcm=wav.readframes(wav.getnframes())
        if channels!=1 or width!=2: raise RuntimeError('Unexpected Windows output format')
        frame=av.AudioFrame.from_ndarray(np.frombuffer(pcm,dtype='<i2').reshape(1,-1),format='s16',layout='mono'); frame.sample_rate=rate
        resampler=av.AudioResampler(format='s16',layout='mono',rate=8000)
        frames=[*resampler.resample(frame),*resampler.resample(None)]
        narrow=b''.join(chunk.to_ndarray().tobytes() for chunk in frames)
        telephone=mulaw_to_pcm(pcm_to_mulaw(narrow))
        started=time.monotonic()
        response=httpx.post('http://127.0.0.1:8000/transcribe',params={'locale':'bg-BG'},content=pcm_16khz(telephone,8000),
            headers={'Authorization':'Bearer '+key},timeout=60,trust_env=False)
        result={'source':source.name,'input_rate':rate,'input_channels':channels,'input_width':width,
                'phone_seconds':len(narrow)/16000,'wall_ms':(time.monotonic()-started)*1000,'status':response.status_code,'actual_stt':response.json(),
                'voice':'installed Microsoft Ivan','live_replacement':False,'human_review':'PENDING'}
        results.append(result); print(json.dumps(result,ensure_ascii=False),flush=True)
        Path('/tmp/phase8-windows-stt-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__': main()
