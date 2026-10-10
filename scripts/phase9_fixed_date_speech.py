"""Synthetic absolute-date telephone-band probes; no conversation or booking writes."""
import json
import argparse
from pathlib import Path
import sys
import time
import wave
sys.path.insert(0,'/app')
import httpx
from backend.assistant.audio import mulaw_to_pcm,pcm_16khz

CASES=[('bg-BG','bg15','Здравейте, искам да запиша час за 13 октомври 2026 в 15 часа.'),
       ('en-US','en16','Hello, I would like to book an appointment for October 13, 2026 at four PM.'),
       ('bg-BG','bg17','Искам да запиша час за 13 октомври 2026 в 17 часа.')]
SPELLED_CASES=[('bg-BG','bg15','Здравейте, искам час за тринадесети октомври две хиляди двадесет и шест година в петнадесет часа.'),
       ('en-US','en16','Hello, I would like to book an appointment for October thirteen two thousand twenty six at four PM.'),
       ('bg-BG','bg17','Искам час за тринадесети октомври две хиляди двадесет и шест година в седемнадесет часа.')]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--spelled',action='store_true');args=parser.parse_args()
    directory=Path('/tmp/phase9-fixed-dates-spelled' if args.spelled else '/tmp/phase9-fixed-dates');directory.mkdir(exist_ok=True)
    key=Path('/run/secrets/speech_key').read_text().strip();records=[]
    with httpx.Client(timeout=70,trust_env=False,headers={'Authorization':'Bearer '+key}) as client:
        for locale,label,text in SPELLED_CASES if args.spelled else CASES:
            started=time.monotonic()
            response=client.post('http://172.30.7.5:8000/synthesize',params={'locale':locale},json={'text':text,'voice':'bgtts-bg' if locale=='bg-BG' else 'bgtts-en'})
            response.raise_for_status();pcm=mulaw_to_pcm(response.content)+b'\0'*32000
            row={'locale':locale,'label':label,'expected_text':text,'tts_ms':(time.monotonic()-started)*1000,'synthetic_only':True}
            with wave.open(str(directory/(label+'.wav')),'wb') as wav:
                wav.setparams((1,2,8000,0,'NONE','not compressed'));wav.writeframes(pcm)
            started=time.monotonic()
            recognition=client.post('http://172.30.7.4:8000/transcribe',params={'locale':locale},content=pcm_16khz(pcm,8000))
            row.update(stt_ms=(time.monotonic()-started)*1000,stt_status=recognition.status_code,actual_stt=recognition.json())
            records.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
            (directory/'results.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
