"""Convert authorized Windows evaluation caller WAVs to actual phone-band inputs."""
import base64
import json
from pathlib import Path
import sys
import time
import wave
import importlib.util
sys.path.insert(0,'/app')
import av
import httpx
import numpy as np
from backend.assistant.audio import TurnBuffer, pcm_to_mulaw, mulaw_to_pcm, pcm_16khz
from backend.assistant.domain import AudioFrame


def main():
    root=Path('/tmp/phase8b'); out=root/'call-input'; out.mkdir(exist_ok=True)
    # STT image remains unchanged; evaluate the current backend's trusted VAD
    # source in this test process without patching the running speech service.
    spec=importlib.util.spec_from_file_location('backend.assistant.phase8b_fixture_audio',root/'voice_audio.py')
    audio_module=importlib.util.module_from_spec(spec); spec.loader.exec_module(audio_module)
    key=Path('/run/secrets/speech_key').read_text().strip()
    results=[]
    for source,target in [(root/'windows-voice/bg-BG-affirm.wav',out/'bg-BG-confirm.wav'),
                          (root/'windows-caller/bg-BG-request-late.wav',out/'bg-BG-request-late.wav')]:
        with wave.open(str(source)) as wav:
            rate=wav.getframerate(); pcm=wav.readframes(wav.getnframes())
        frame=av.AudioFrame.from_ndarray(np.frombuffer(pcm,dtype='<i2').reshape(1,-1),format='s16',layout='mono'); frame.sample_rate=rate
        converter=av.AudioResampler(format='s16',layout='mono',rate=8000)
        audio=b''.join(f.to_ndarray().tobytes() for f in [*converter.resample(frame),*converter.resample(None)])
        phone=mulaw_to_pcm(pcm_to_mulaw(audio))+b'\0'*32000
        with wave.open(str(target),'wb') as wav:
            wav.setparams((1,2,8000,0,'NONE','not compressed')); wav.writeframes(phone)
        buffer=audio_module.TurnBuffer(silence_ms=1800,pre_roll_ms=200)
        for number,offset in enumerate(range(0,len(phone),320)):
            item,_=buffer.feed(AudioFrame(sequence=number,utterance_id='fixture',encoding='pcm16',sample_rate=8000,
                payload=base64.b64encode(phone[offset:offset+320]).decode()))
            if not item: continue
            started=time.monotonic()
            response=httpx.post('http://127.0.0.1:8000/transcribe',params={'locale':'bg-BG'},
                content=pcm_16khz(item[0],8000),headers={'Authorization':'Bearer '+key},timeout=60,trust_env=False)
            row={'source':source.name,'target':target.name,'status':response.status_code,
                'actual_stt':response.json(),'wall_ms':(time.monotonic()-started)*1000,
                'input':'8k PCMU round-trip through actual 1800ms VAD; known bg; existing STT worker'}
            results.append(row); print(json.dumps(row,ensure_ascii=False),flush=True)
    (root/'call-input-stt.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__': main()
