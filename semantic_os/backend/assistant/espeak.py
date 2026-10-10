"""Commercial-compatible GPL-3.0-or-later formant baseline; audible quality needs review."""
import io
import re
import subprocess
from threading import BoundedSemaphore
from time import monotonic
import unicodedata
import wave
from .audio import pcm_to_mulaw
from .local_speech import resample_pcm
from .domain import Capability, DomainError


def spoken_text(text, locale):
    text=unicodedata.normalize('NFC',text).replace('Europe/Sofia','българско време' if locale=='bg-BG' else 'Sofia time')
    text=re.sub(r'\b[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}\b','',text,flags=re.I)
    if locale=='bg-BG':
        months=('януари','февруари','март','април','май','юни','юли','август','септември','октомври','ноември','декември')
        def date(match):
            day,month,year=map(int,match.groups())
            return f'{day} {months[month-1]} {year} година' if 1<=month<=12 and 1<=day<=31 else match[0]
        text=re.sub(r'\b(\d{2})\.(\d{2})\.(\d{4})\b',date,text)
        def clock(match):
            hour,minute=map(int,match.groups())
            return f'{hour} часа'+(f' и {minute} минути' if minute else '')
        text=re.sub(r'\b(\d{1,2}):(\d{2})\b',clock,text)
    return text.replace('[[','').replace(']]','')


class EspeakProvider:
    capability=Capability('espeak_ng','LIVE_UNVERIFIED',features=('local_formant_mulaw',),limitations=('robotic_voice','listening_review_required'))
    voice_ids={'bg-BG':'espeak-bg','en-US':'espeak-en'}
    def __init__(self, executable='espeak-ng', *, timeout=10):
        self.executable,self.timeout,self.slot=executable,timeout,BoundedSemaphore(1)
        self.last_metrics={}
        for locale,voice in (('bg-BG','bg'),('en-US','en-us')):
            result=subprocess.run([executable,'--voices='+voice],capture_output=True,timeout=timeout)
            if result.returncode or len(result.stdout.splitlines())<2: raise DomainError('unsupported_locale',422)

    def wav(self, text, locale, voice):
        if locale not in self.voice_ids or voice!=self.voice_ids[locale]: raise DomainError('unsupported_locale',422)
        if not text.strip() or len(text)>2000: raise DomainError('invalid_input',422)
        if not self.slot.acquire(timeout=self.timeout): raise DomainError('timeout',504)
        start=monotonic()
        try:
            result=subprocess.run([self.executable,'-v',{'bg-BG':'bg','en-US':'en-us'}[locale],'-s','165','--stdout','--stdin'],
                input=spoken_text(text,locale).encode(),capture_output=True,timeout=self.timeout)
            if result.returncode or not 44<len(result.stdout)<=6_000_000: raise DomainError('provider_error',502)
            self.last_metrics={'batch_synthesis_ms':(monotonic()-start)*1000,'first_audio_ms':None,'state':'LIVE_UNVERIFIED'}
            return result.stdout
        except subprocess.TimeoutExpired: raise DomainError('timeout',504) from None
        finally: self.slot.release()

    def synthesize(self, text, locale, voice=None):
        raw=self.wav(text,locale,voice)
        with wave.open(io.BytesIO(raw),'rb') as wav:
            rate=wav.getframerate()
            if wav.getnchannels()!=1 or wav.getsampwidth()!=2 or not 8000<=rate<=48000: raise DomainError('unsupported_audio',422)
            pcm=wav.readframes(60*rate+1)
            if len(pcm)>60*rate*2: raise DomainError('limit_reached',413)
        return pcm_to_mulaw(resample_pcm(pcm,rate))
