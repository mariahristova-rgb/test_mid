"""Actual local synthesis samples, explicitly not a SIP or intelligibility pass."""
import argparse
import io
import json
from pathlib import Path
import wave
from backend.assistant.espeak import EspeakProvider

def main(directory):
    directory.mkdir(parents=True,exist_ok=True)
    provider=EspeakProvider()
    phrases={
        'bg-BG':[('greeting','Здравейте! Свързахте се със SmileCare. Как мога да Ви помогна?'),
            ('request','Искам да запиша час за следващия понеделник в 15:00.'),
            ('name','Казвам се Мария Демо.'),('confirm','Потвърждавам.'),
            ('confirmation','Мария Демо, часът Ви е потвърден за 12.10.2026 в 15:00, българско време.')],
        'en-US':[('greeting','Hello! You have reached SmileCare. How can I help you?'),
            ('request','Hello, I would like to book a dental checkup next Monday at 3 PM.'),
            ('name','My name is Jane Example.'),('confirm','I confirm.'),
            ('confirmation','Jane Example, your dental checkup is confirmed for October 12, 2026 at 3 PM.')]
    }
    results=[]
    for locale,values in phrases.items():
        for name,text in values:
            raw=provider.wav(text,locale,provider.voice_ids[locale])
            with wave.open(io.BytesIO(raw),'rb') as source:
                rate=source.getframerate(); pcm=source.readframes(60*rate)
            path=directory/(locale+'-'+name+'.wav')
            with wave.open(str(path),'wb') as target:
                target.setnchannels(1); target.setsampwidth(2); target.setframerate(rate); target.writeframes(pcm)
            results.append({'locale':locale,'phrase':name,'sample_rate':rate,'duration_seconds':len(pcm)/(rate*2),
                'audio':path.name,**provider.last_metrics,'intelligibility':'LISTENING_REVIEW_REQUIRED'})
    (directory/'tts-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--directory',type=Path,required=True)
    main(parser.parse_args().directory)
