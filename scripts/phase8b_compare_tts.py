"""Current response-provider comparison on the same authorized evaluation phrases."""
import json
from pathlib import Path
import sys
import time
import wave
sys.path.insert(0,'/app')
import httpx
from backend.assistant.audio import mulaw_to_pcm, pcm_16khz


def main():
    root=Path('/tmp/phase8b-current-tts');root.mkdir(exist_ok=True)
    key=Path('/run/secrets/speech_key').read_text().strip()
    cases=json.loads(Path('/tmp/phase8b-cases.json').read_text(encoding='utf-8'))
    results=[]
    with httpx.Client(timeout=70,trust_env=False,headers={'Authorization':'Bearer '+key}) as client:
        for case in cases:
            start=time.monotonic()
            response=client.post('http://172.30.7.5:8000/synthesize',params={'locale':'bg-BG'},json={'text':case['text'],'voice':'bgtts-bg'})
            row={'label':case['label'],'text':case['text'],'tts_status':response.status_code,'tts_http_wall_ms':(time.monotonic()-start)*1000,'provider':'unchanged BG38/MioCodec'}
            if response.status_code==200:
                if response.headers.get('x-audio-encoding')!='mulaw':raise RuntimeError('Unexpected encoding')
                pcm=mulaw_to_pcm(response.content)
                with wave.open(str(root/(case['label']+'.wav')),'wb') as wav:
                    wav.setparams((1,2,8000,0,'NONE','not compressed'));wav.writeframes(pcm)
                row['audio_seconds']=len(pcm)/16000
                start=time.monotonic()
                recognition=client.post('http://172.30.7.4:8000/transcribe',params={'locale':'bg-BG'},content=pcm_16khz(pcm,8000))
                row.update(stt_status=recognition.status_code,stt_wall_ms=(time.monotonic()-start)*1000,actual_stt=recognition.json())
            results.append(row)
            (root/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(row,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
