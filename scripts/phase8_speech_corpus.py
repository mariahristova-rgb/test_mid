"""Inside the owned backend: actual current TTS and known-locale STT, synthetic data only."""
from datetime import datetime,timezone
import json
from pathlib import Path
import time
import wave
import httpx
from backend.assistant.audio import mulaw_to_pcm,pcm_16khz

CASES=[('bg-BG','stt-greeting','Здравейте, искам да запиша час.'),
 ('bg-BG','stt-weekday','Имате ли свободен час в понеделник?'),
 ('bg-BG','stt-clock','Искам час в петнадесет часа.'),
 ('bg-BG','stt-name','Казвам се Мария Иванова.'),
 ('bg-BG','stt-confirm','Да, потвърждавам резервацията.'),
 ('bg-BG','tts-greeting','Здравейте! Как мога да Ви помогна?'),
 ('bg-BG','tts-available','Имате свободен час в понеделник в петнадесет часа.'),
 ('bg-BG','tts-success','Вашият час е успешно записан.'),
 ('bg-BG','tts-goodbye','Благодаря Ви! Приятен ден!'),
 ('bg-BG','booking','Здравейте, искам да запиша час за профилактичен преглед следващия понеделник в петнадесет часа.'),
 ('en-US','booking','Hello, I would like to book a dental checkup next Monday at three PM.'),
 ('en-US','name','My name is Jane Smith.'),('en-US','confirm','Yes, I confirm the appointment.'),
 ('en-US','switch','Please continue in English.')]


def main():
    out=Path('/tmp/phase8-corpus'); out.mkdir(exist_ok=True)
    key=Path('/run/secrets/speech_key').read_text().strip()
    records=[]
    with httpx.Client(timeout=70,trust_env=False,headers={'Authorization':'Bearer '+key}) as client:
        for locale,label,text in CASES:
            started=time.monotonic(); first=None; chunks=[]
            with client.stream('POST','http://172.30.7.5:8000/synthesize',params={'locale':locale},
                    json={'text':text,'voice':'bgtts-bg' if locale=='bg-BG' else 'bgtts-en'}) as response:
                response.raise_for_status()
                if response.headers.get('x-audio-encoding')!='mulaw' or response.headers.get('x-sample-rate')!='8000':
                    raise RuntimeError('Unexpected negotiated speech format')
                for chunk in response.iter_bytes():
                    if first is None and chunk: first=(time.monotonic()-started)*1000
                    chunks.append(chunk)
            audio=b''.join(chunks); pcm=mulaw_to_pcm(audio)
            target=out/(locale+'-'+label+'.wav')
            with wave.open(str(target),'wb') as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(8000); wav.writeframes(pcm+b'\x00'*32000)
            entry={'locale':locale,'case':label,'expected_text':text,'audio_file':target.name,
                'audio_seconds':len(audio)/8000,'first_audio_http_ms':first,'tts_total_ms':(time.monotonic()-started)*1000,
                'tts_state':'ACTUAL_CPU_BATCH_SYNTHESIS','human_intelligibility':'UNVERIFIED'}
            started=time.monotonic()
            response=client.post('http://172.30.7.4:8000/transcribe',params={'locale':locale},content=pcm_16khz(pcm+b'\x00'*32000,8000))
            entry.update(stt_wall_ms=(time.monotonic()-started)*1000,stt_status=response.status_code,actual_stt=response.json())
            records.append(entry); print(json.dumps(entry,ensure_ascii=False),flush=True)
            (out/'results.json').write_text(json.dumps({'timestamp':datetime.now(timezone.utc).isoformat(),
                'model':'existing BG38/MioCodec and multilingual small','beam_size':1,'device':'cpu','compute_type':'int8',
                'known_locale_hints':True,'synthetic_only':True,'cases':records},ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__': main()
