"""Infrastructure implementations: deterministic mocks only; no live charges."""
from dataclasses import asdict
from html import escape
import hashlib
import hmac
import json
import re
from .domain import Capability, DomainError, Message, Locale, BookingIntent
from .language import tr
from contextlib import contextmanager
from dataclasses import replace
from threading import RLock
from ..agents.llm.provider import ChatMessage, GenerationRequest, GenerationResponse

GSM_BASIC = set('@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !"#¤%&\'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà')
GSM_EXT = set('^{}\\[~]|€\f')


def sms_segments(text: str) -> dict:
    gsm = all(c in GSM_BASIC or c in GSM_EXT for c in text)
    units = sum(2 if c in GSM_EXT else 1 for c in text) if gsm else len(text.encode('utf-16-be')) // 2
    single, multipart = (160, 153) if gsm else (70, 67)
    segments = 0 if not units else (1 if units <= single else (units + multipart - 1) // multipart)
    return {'encoding': 'GSM-7' if gsm else 'UCS-2', 'units': units, 'segments': segments,
            'cost_units': segments, 'price': None}


def e164(value: str) -> str:
    value = re.sub(r'[ ()-]', '', value)
    if not re.fullmatch(r'\+[1-9]\d{7,14}', value):
        raise DomainError('invalid_input', 422)
    return value


def safe_email_html(text: str) -> str:
    return '<p>' + escape(text).replace('\n', '<br>') + '</p>'


class MockLLMProvider:
    capability = Capability('mock', 'MOCK', features=('text', 'deterministic'))

    def reply(self, text: str, locale: Locale, instructions: str = '') -> str:
        # Untrusted text is never interpreted as authorization or arbitrary tool arguments.
        request = GenerationRequest(messages=[ChatMessage(role='system', content=instructions),
                                    ChatMessage(role='user', content=text)], metadata={'locale': locale})
        return self.generate(request).text

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        locale = request.metadata.get('locale', 'en-US')
        if locale not in self.capability.locales:
            raise DomainError('unsupported_locale', 422)
        text = str(request.messages[-1].content).casefold() if request.messages else ''
        key = 'hello'
        if any(word in text for word in ('cancel', 'отмен', 'отмяна')):
            key = 'cancel_details'
        elif any(word in text for word in ('reschedule', 'премест', 'преместване')):
            key = 'reschedule_details'
        elif any(word in text for word in ('human', 'човек', 'оператор')):
            key = 'human_details'
        elif any(word in text for word in ('appointment', 'час', 'записване')):
            key = 'appointment_details'
        return GenerationResponse(text=tr(locale, key), model='deterministic-mock')

    def interpret_booking(self, request):
        """Constrained synthetic parser: suggestions never grant execution permissions."""
        text = request.content.strip()
        lower = text.casefold().strip(' .!')
        if lower in {'yes', 'yes, confirm', 'yes confirm', 'confirm', 'i confirm', 'да', 'да, потвърждавам', 'да потвърждавам', 'потвърждавам'}:
            return BookingIntent(intent='confirm')
        if lower in {'cancel', 'never mind', 'no', 'отказ', 'откажи', 'отказвам', 'не'}:
            return BookingIntent(intent='cancel')
        booking = bool(re.search(r'\b(?:book|booking|appointment|запиша|запиши|записване|резервирам|резервирай)\b', lower)
                       or re.search(r'\b(?:искам|желая)\b.*\bчас\b', lower))
        if re.search(r'\b(?:cancel|reschedule|отменя|преместя)\b', lower):
            booking = False
        date_text = None
        match = re.search(r'\b(?:(next|следващия)\s+)?(утре|днес|tomorrow|today|понеделник|вторник|сряда|четвъртък|петък|събота|неделя|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+(?:(?:в|at)\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)|\d{1,2}:\d{2})(?!\d)', lower)
        if match:
            date_text = ((match[1] + ' ') if match[1] else '') + match[2] + ' ' + match[3]
        else:
            match = re.search(r'\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?', text)
            if not match:
                match = re.search(r'\b\d{2}\.\d{2}\.\d{4}\s+\d{1,2}:\d{2}', text) if request.locale == 'bg-BG' else re.search(r'\b\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}\s+(?:AM|PM)', text, re.I)
            if match:
                date_text = match[0]
        name = None
        match = re.search(r'(?:казвам се|името ми е|аз съм|my name is|name is|i am)\s+([^.,;!?]+)', text, re.I)
        if match:
            candidate = match[1].strip()
            if len(candidate) <= 120 and not re.search(r'\d|[=<>]', candidate):
                name = candidate
        elif request.collecting_name and re.fullmatch(r'[^\W\d_]+(?:[ \-\'][^\W\d_]+){0,5}', text, re.U) and lower not in {'hello', 'thanks', 'здравейте', 'благодаря', 'ok'} and not re.match(r'^(?:what|when|why|how|please|switch|continue|как|кога|защо|кой|може|премини|продължи)\b', lower):
            name = text
        duration = None
        parts = re.findall(r'\b\d+\s*(?:hours?|minutes?|часове|часа|час|минути|минута|мин)\b', lower)
        if parts:
            from .language import parse_duration
            duration = parse_duration(' '.join(parts), request.locale)
        day = re.search(r'\b(?:(?:next|следващия)\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday|понеделник|вторник|сряда|четвъртък|петък|събота|неделя|tomorrow|утре)\b', lower)
        if not date_text:
            time_only = re.fullmatch(r'(?:(?:at|в)\s+)?(\d{1,2}:\d{2})', lower)
            if time_only: date_text = time_only[1]
        return BookingIntent(intent='book' if booking else 'details' if date_text or name or duration or day else 'none',
                             date_text=date_text, day_text=day[0] if day and not date_text else None, contact_name=name, duration_minutes=duration)


class MockSpeechProvider:
    capability = Capability('mock', 'MOCK', features=('synthetic_transcript', 'synthetic_audio'))

    def transcribe(self, sample: bytes, locale: Locale) -> str:
        self.require(locale)
        return sample.decode('utf-8')  # Synthetic UTF-8 fixture, not speech recognition.

    def synthesize(self, text: str, locale: Locale, voice=None) -> bytes:
        self.require(locale)
        if voice and voice != {'bg-BG': 'mock-bg', 'en-US': 'mock-en'}[locale]:
            raise DomainError('unsupported_locale', 422)
        return text.encode('utf-8')  # Synthetic fixture, not playable speech.

    def require(self, locale):
        if locale not in self.capability.locales:
            raise DomainError('unsupported_locale', 422)


class MockTelephonyProvider:
    capability = Capability('mock', 'MOCK', features=('sip_extension_point', 'transfer', 'barge_in'))
    def start(self, call_id, locale):
        return {'call_id': call_id, 'status': 'listening', 'provider': 'mock'}
    def transfer(self, call_id, destination):
        return {'call_id': call_id, 'status': 'transferred', 'provider': 'mock'}
    def terminate(self, call_id):
        return {'call_id': call_id, 'status': 'ended', 'provider': 'mock'}


class MockChannelAdapter:
    """Signed mock contract; never claimed to be a vendor webhook implementation."""
    def __init__(self, channel):
        self.channel = channel
        self.capability = Capability('mock', 'MOCK', features=('inbound', 'outbound', 'status_callbacks'))

    def verify_signature(self, body: bytes, signature: str, secret: str) -> bool:
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return bool(secret and signature) and hmac.compare_digest(expected, signature)

    def normalize(self, payload: dict) -> Message:
        message = Message.model_validate(payload)
        if message.channel.value != self.channel or message.provider != 'mock':
            raise DomainError('invalid_input', 422)
        if self.channel in ('sms', 'whatsapp'):
            message.sender, message.recipient = e164(message.sender), e164(message.recipient)
        return message

    def resolve_conversation(self, message: Message) -> str:
        return message.conversation_id

    def send(self, message: Message) -> dict:
        result = {'provider': 'mock', 'state': 'MOCK', 'status': 'simulated', 'external_id': 'mock:' + message.id}
        if self.channel in ('sms', 'whatsapp'):
            e164(message.recipient)
        if self.channel == 'sms':
            result.update(sms_segments(message.content))
        if self.channel == 'email':
            if '@' not in message.recipient or '\r' in message.recipient or '\n' in message.recipient:
                raise DomainError('invalid_input', 422)
            result.update(subject=tr(message.locale, 'subject'), html=safe_email_html(message.content),
                          thread_id=message.conversation_id)
        if self.channel == 'whatsapp':
            window = message.metadata.get('window_open', False)
            template = message.metadata.get('approved_template')
            if not window and not template:
                raise DomainError('provider_error', 422)
            result['template_locale'] = {'bg-BG': 'bg', 'en-US': 'en_US'}[message.locale]
        return result

    def status_callback(self, payload: dict) -> dict:
        if payload.get('status') not in ('sent', 'delivered', 'failed', 'read') or not payload.get('external_id'):
            raise DomainError('invalid_input', 422)
        return {'external_id': payload['external_id'], 'status': payload['status'], 'provider': 'mock'}

    def provider_error(self, code: str) -> dict:
        return {'code': 'provider_error', 'retryable': code == 'temporary', 'provider': 'mock'}


class MockVoiceAdapter(MockChannelAdapter):
    def __init__(self): super().__init__('voice')

class LocalVoiceAdapter(MockVoiceAdapter):
    capability=Capability('local_voice','LIVE_UNVERIFIED',features=('queued_audio',),limitations=('transport_receipt_required',))
    def __init__(self):
        self.channel='voice'
    def send(self,message):
        if message.channel.value!='voice': raise DomainError('invalid_input',422)
        return {'provider':'local_voice','state':'LIVE_UNVERIFIED','status':'queued_for_audio','external_id':message.id}


class MockEmailAdapter(MockChannelAdapter):
    def __init__(self): super().__init__('email')


class MockWhatsAppAdapter(MockChannelAdapter):
    def __init__(self): super().__init__('whatsapp')


class MockSMSAdapter(MockChannelAdapter):
    def __init__(self): super().__init__('sms')


class WebChatAdapter(MockChannelAdapter):
    def __init__(self): super().__init__('web_chat')


class ProviderRegistry:
    def __init__(self):
        self.llm = MockLLMProvider()
        self.speech = MockSpeechProvider()
        self.telephony = MockTelephonyProvider()
        self.calendar = None  # Bound to tenant-scoped persistence in the composition layer.
        self.qwen_settings, self.qwen_secret, self.qwen_transport = None, '', None
        self.active_llms, self.llm_lock = {}, RLock()
        self.local_stt, self.local_tts, self.asterisk = None, None, None

        self.channels = {item.channel: item for item in (
            MockVoiceAdapter(), MockEmailAdapter(), MockWhatsAppAdapter(), MockSMSAdapter(), WebChatAdapter())}

    def configure_calendar(self, store):
        if self.calendar is None:
            from .calendar import MockCalendarProvider
            self.calendar = MockCalendarProvider(store)

    def describe(self):
        items = [{'kind': 'llm', **asdict(self.llm.capability)},
                 {'kind': 'stt', **asdict(self.speech.capability)},
                 {'kind': 'tts', **asdict(self.speech.capability)},
                 {'kind': 'telephony', **asdict(self.telephony.capability)}]
        if self.qwen_settings:
            from .qwen import QwenProvider
            items[0] = {'kind': 'llm', **asdict(QwenProvider.capability)}
        for index, provider in ((1, self.local_stt), (2, self.local_tts), (3, self.asterisk)):
            if provider: items[index] = {**asdict(provider.capability), 'kind': items[index]['kind']}
        return items + [{'kind': key, **asdict(value.capability)} for key, value in self.channels.items()]

    def require(self, provider: str, locale: str):
        if provider not in ('mock', 'qwen') or provider == 'qwen' and self.qwen_settings is None:
            raise DomainError('unconfigured', 422)
        if locale not in self.llm.capability.locales:
            raise DomainError('unsupported_locale', 422)

    def configure_qwen(self, settings, *, secret='', transport=None):
        settings.validate()
        self.qwen_settings, self.qwen_secret, self.qwen_transport = settings, secret, transport

    @contextmanager
    def llm_session(self, assistant, conversation, principal, store, correlation):
        self.require(assistant['llm_provider'], conversation['active_locale'])
        if assistant['llm_provider'] == 'mock':
            yield self.llm
            return
        from .qwen import QwenProvider
        settings = assistant.get('llm_settings', {})
        model = settings.get('model', 'Qwen3-4B')
        # An assistant selects only a deployment-owned model alias, never a URL or secret.
        if model != self.qwen_settings.model_name:
            raise DomainError('unconfigured', 503)
        if set(settings) - {'model', 'temperature', 'max_tokens'}:
            raise DomainError('invalid_input', 422)
        maximum = settings.get('max_tokens', self.qwen_settings.max_output_tokens)
        temperature = settings.get('temperature', .2)
        if type(maximum) is not int or maximum < 1 or not isinstance(temperature, (int, float)) or not 0 <= temperature <= 1:
            raise DomainError('invalid_input', 422)
        bounded = replace(self.qwen_settings, max_output_tokens=min(maximum, self.qwen_settings.max_output_tokens))
        context = {'tenant_id': principal.tenant_id, 'assistant_id': assistant['id'], 'conversation_id': conversation['id'],
            'call_id': conversation.get('call_session_id'), 'correlation_id': correlation, 'channel': conversation['channel']}
        observed = {'llm_input_tokens':0, 'llm_output_tokens':0}
        def budget(body):
            if store.entitlements:
                maximum_input = len(json.dumps(body, ensure_ascii=False).encode())+256
                store.entitlements.check(principal.tenant_id, 'llm_input_tokens', observed['llm_input_tokens']+maximum_input)
                store.entitlements.check(principal.tenant_id, 'llm_output_tokens', observed['llm_output_tokens']+body['max_tokens'])
        def measured(receipt):
            reported = receipt['usage_reported']
            for category, key in (('llm_input_tokens','prompt_tokens'),('llm_output_tokens','completion_tokens')):
                if reported: observed[category] += receipt[key]
            record = {**context, **receipt, 'kind': 'llm_inference', 'provider': 'qwen',
                'llm_input_tokens': receipt['prompt_tokens'], 'llm_output_tokens': receipt['completion_tokens'],
                'token_usage_status': 'reported' if reported else 'unreported', 'timestamp': now(), 'billing_precharged': True}
            def persist():
                if not store.find('usage_records', principal.tenant_id, 'llm:' + receipt['request_id']):
                    store.add('usage_records', principal.tenant_id, record, external_key='llm:' + receipt['request_id'])
            store.after_transaction(persist)
            if not reported and receipt['inference_outcome'] != 'failed' and store.entitlements and store.entitlements.plan(principal.tenant_id):
                raise DomainError('provider_error', 502)  # A metered plan cannot safely continue with unreported token usage.
        from .store import now
        provider = QwenProvider(bounded, secret=self.qwen_secret, transport=self.qwen_transport, usage_sink=measured,
            context=context, temperature=temperature, budget_guard=budget)
        key = (principal.tenant_id, conversation.get('call_session_id') or conversation['id'])
        with self.llm_lock:
            if key in self.active_llms: raise DomainError('conflict', 409)
            self.active_llms[key] = provider
        try: yield provider
        finally:
            with self.llm_lock: self.active_llms.pop(key, None)

    def cancel_llm(self, tenant_id, call_id):
        with self.llm_lock:
            provider = self.active_llms.get((tenant_id, call_id))
            if provider: provider.cancel()
