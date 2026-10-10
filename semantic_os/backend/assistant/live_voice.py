"""Gated provider infrastructure. No network operation without explicit live configuration."""
import base64
import hashlib
import hmac
import io
import json
import re
from urllib.parse import parse_qsl, urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError
import wave
from xml.sax.saxutils import escape
from .domain import Capability, DomainError


def http_request(url, body, headers, timeout=8):
    try:
        with urlopen(Request(url, data=body, headers=headers, method='POST'), timeout=timeout) as response:
            result = response.read(4_000_001)
            if len(result) > 4_000_000:
                raise DomainError('provider_error', 502)
            return result
    except (URLError, TimeoutError, OSError):
        # Provider exceptions/URLs/headers may carry credentials. Return only a safe code.
        raise DomainError('provider_error', 502) from None


class AzureSpeechProvider:
    capability = Capability('azure', 'LIVE_UNVERIFIED', features=('utterance_stt', 'tts'),
                            limitations=('final_results_only', 'real_samples_unverified'))
    VOICES = {'bg-BG': ('bg-BG-KalinaNeural', 'bg-BG-BorislavNeural'),
              'en-US': ('en-US-JennyNeural', 'en-US-GuyNeural')}

    def __init__(self, key, resource, region, *, enabled=False, http=http_request):
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,60}', resource) or not re.fullmatch(r'[a-z0-9]{2,30}', region):
            raise DomainError('invalid_input', 422)
        self.key, self.resource, self.region, self.enabled, self.http = key, resource, region, enabled, http

    def require(self, locale):
        if locale not in self.capability.locales:
            raise DomainError('unsupported_locale', 422)
        if not self.enabled or not self.key:
            raise DomainError('unconfigured', 503)

    def transcribe(self, sample, locale):
        """16kHz mono PCM, limited to 30 seconds by the pipeline. No partial results."""
        self.require(locale)
        if len(sample) % 2 or len(sample) > 960000:
            raise DomainError('invalid_input', 422)
        output = io.BytesIO()
        with wave.open(output, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(sample)
        endpoint = f'https://{self.resource}.cognitiveservices.azure.com/stt/speech/recognition/conversation/cognitiveservices/v1?language={locale}&format=simple'
        raw = self.http(endpoint, output.getvalue(), {'Ocp-Apim-Subscription-Key': self.key,
            'Content-Type': 'audio/wav; codecs=audio/pcm; samplerate=16000', 'Accept': 'application/json'})
        try:
            result = json.loads(raw)
            text = result.get('DisplayText', '') if result.get('RecognitionStatus') == 'Success' else ''
            if not isinstance(text, str) or len(text) > 10000:
                raise ValueError()
            return text
        except (ValueError, AttributeError):
            raise DomainError('provider_error', 502) from None

    def synthesize(self, text, locale, voice=None):
        self.require(locale)
        voice = voice or self.VOICES[locale][0]
        if voice not in self.VOICES[locale] or len(text) > 10000:
            raise DomainError('unsupported_locale', 422)
        ssml = f'<speak version="1.0" xml:lang="{locale}"><voice name="{voice}">{escape(text)}</voice></speak>'
        return self.http(f'https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1', ssml.encode(), {
            'Ocp-Apim-Subscription-Key': self.key, 'Content-Type': 'application/ssml+xml',
            'X-Microsoft-OutputFormat': 'raw-8khz-8bit-mono-mulaw', 'User-Agent': 'AssistantVoice'})


class TwilioTelephonyProvider:
    capability = Capability('twilio', 'LIVE_UNVERIFIED', features=('incoming', 'bidirectional_media', 'sip_compatible', 'transfer'),
                            limitations=('test_account_and_number_required', 'real_calls_unverified'))

    def __init__(self, account_sid, auth_token, *, enabled=False, http=http_request):
        if not re.fullmatch(r'AC[0-9a-fA-F]{32}', account_sid):
            raise DomainError('invalid_input', 422)
        self.account_sid, self.auth_token, self.enabled, self.http = account_sid, auth_token, enabled, http

    def verify_webhook(self, url, body, signature):
        try:
            fields = parse_qsl(body.decode(), keep_blank_values=True, strict_parsing=True, max_num_fields=128)
            if len({key for key, _ in fields}) != len(fields):
                return False  # Reject ambiguous duplicate parameters rather than interpreting them differently.
            value = url + ''.join(key + content for key, content in sorted(fields))
            expected = base64.b64encode(hmac.new(self.auth_token.encode(), value.encode(), hashlib.sha1).digest()).decode()
            return bool(signature and self.auth_token) and hmac.compare_digest(expected, signature)
        except (ValueError, UnicodeError):
            return False

    def start(self, call_id, locale):
        return {'call_id': call_id, 'status': 'listening', 'provider': 'twilio'}

    def _update(self, call_id, fields):
        if not self.enabled:
            raise DomainError('unconfigured', 503)
        if not re.fullmatch(r'CA[0-9a-fA-F]{32}', call_id):
            raise DomainError('invalid_input', 422)
        authorization = base64.b64encode((self.account_sid + ':' + self.auth_token).encode()).decode()
        self.http(f'https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Calls/{call_id}.json',
                  urlencode(fields).encode(), {'Authorization': 'Basic ' + authorization,
                                               'Content-Type': 'application/x-www-form-urlencoded'})

    def transfer(self, call_id, destination):
        if not re.fullmatch(r'\+[1-9]\d{7,14}', destination):
            raise DomainError('invalid_input', 422)
        self._update(call_id, {'Twiml': f'<Response><Dial><Number>{destination}</Number></Dial></Response>'})
        return {'status': 'transferred', 'provider': 'twilio'}

    def terminate(self, call_id):
        self._update(call_id, {'Status': 'completed'})
        return {'status': 'ended', 'provider': 'twilio'}


def stream_twiml(public_origin, ticket):
    url = public_origin.replace('https://', 'wss://', 1) + '/voice/media'
    return ('<Response><Connect><Stream url="' + escape(url, {'"': '&quot;'}) + '">'
            '<Parameter name="ticket" value="' + escape(ticket, {'"': '&quot;'}) + '"/>'
            '</Stream></Connect></Response>')
