"""Private local-engine workers. No tenant-supplied endpoints or managed providers."""
from ipaddress import ip_address
from urllib.parse import urlsplit
import httpx
from .domain import Capability, DomainError, LOCALES


class LocalSpeechHTTP:
    def __init__(self, endpoint, secret, kind, *, transport=None, timeout=20):
        url=urlsplit(endpoint)
        try: address=ip_address(url.hostname)
        except ValueError: raise DomainError('invalid_input',422) from None
        if (url.scheme not in ('http','https') or not address.is_private or address.is_unspecified or address.is_link_local
                or url.username or url.password or url.query or url.fragment or url.path not in ('','/') or not secret):
            raise DomainError('invalid_input',422)
        if kind not in ('faster_whisper','espeak_ng','bgtts38'): raise DomainError('unconfigured',503)
        self.endpoint,self.secret,self.kind,self.transport,self.timeout=endpoint.rstrip('/'),secret,kind,transport,timeout
        self.capability=Capability(kind,'LIVE_UNVERIFIED',features=('local_worker','language_detection') if kind=='faster_whisper' else ('local_worker',),limitations=('real_audio_acceptance_required',))
        if kind=='espeak_ng': self.voice_ids={'bg-BG':'espeak-bg','en-US':'espeak-en'}
        if kind=='bgtts38': self.voice_ids={'bg-BG':'bgtts-bg','en-US':'bgtts-en'}

    def require(self, locale):
        if locale not in LOCALES: raise DomainError('unsupported_locale',422)

    def request(self, path, locale, **kwargs):
        if locale is not None: self.require(locale)
        elif self.kind!='faster_whisper': raise DomainError('unsupported_locale',422)
        try:
            with httpx.Client(transport=self.transport,timeout=self.timeout,follow_redirects=False) as client:
                response=client.post(self.endpoint+path,params={'locale':locale or 'auto'},headers={'Authorization':'Bearer '+self.secret},**kwargs)
                if response.status_code!=200: raise DomainError('provider_error',502)
                if len(response.content)>1_000_000: raise DomainError('invalid_model_output',502)
                return response
        except httpx.TimeoutException: raise DomainError('timeout',504) from None
        except httpx.HTTPError: raise DomainError('provider_error',502) from None

    def transcribe(self, pcm, locale):
        if self.kind!='faster_whisper' or len(pcm)%2 or not 0<len(pcm)<=30*32000: raise DomainError('unsupported_audio',422)
        response=self.request('/transcribe',locale,content=pcm)
        try:
            data=response.json()
            if data.get('locale')!=(locale or 'auto') or not isinstance(data.get('text'),str) or len(data['text'])>10000: raise ValueError()
            return data['text']
        except (ValueError,TypeError): raise DomainError('provider_error',502) from None

    def synthesize(self, text, locale, voice=None):
        if self.kind not in ('espeak_ng','bgtts38') or voice!=self.voice_ids.get(locale) or not 0<len(text)<=2000: raise DomainError('unsupported_locale',422)
        response=self.request('/synthesize',locale,json={'text':text,'voice':voice})
        if response.headers.get('x-audio-encoding')!='mulaw' or response.headers.get('x-sample-rate')!='8000' or not response.content:
            raise DomainError('unsupported_audio',422)
        return response.content
