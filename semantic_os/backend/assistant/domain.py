"""Language-neutral contracts. No provider SDKs or persistence imports."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any, Literal, Protocol
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from zoneinfo import ZoneInfo

Locale = Literal['bg-BG', 'en-US']
LOCALES = ('bg-BG', 'en-US')


class Channel(str, Enum):
    VOICE = 'voice'
    EMAIL = 'email'
    WHATSAPP = 'whatsapp'
    SMS = 'sms'
    WEB_CHAT = 'web_chat'


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid')


class LegacyChannelAdapter(Protocol):
    def verify_signature(self, body: bytes, signature: str, secret: str) -> bool: ...
    def normalize(self, payload: dict) -> 'Message': ...
    def resolve_conversation(self, message: 'Message') -> str: ...
    def send(self, message: 'Message') -> dict: ...
    def status_callback(self, payload: dict) -> dict: ...
    def provider_error(self, code: str) -> dict: ...


class ChannelAdapter(Protocol):
    def validate_inbound_event(self, body: bytes, headers: dict, connection: dict, credentials: dict) -> None: ...
    def normalize_inbound_event(self, body: bytes, connection: dict, received_at: datetime) -> list['NormalizedInbound']: ...
    def resolve_channel_connection(self, connection: dict, recipient_id: str) -> None: ...
    def send_message(self, message: 'Message', connection: dict, credentials: dict, idempotency_key: str) -> dict: ...
    def process_delivery_status(self, payload: dict) -> dict: ...
    def handle_provider_error(self, code: str) -> dict: ...


class EmailProvider(Protocol):
    def send_message(self, message: dict, connection: dict, credentials: dict, idempotency_key: str) -> dict: ...


class SMSProvider(Protocol):
    def send_message(self, message: dict, connection: dict, credentials: dict, idempotency_key: str) -> dict: ...


class FAQEntry(Contract):
    question_bg: str = Field(min_length=1, max_length=500)
    question_en: str = Field(min_length=1, max_length=500)
    answer_bg: str = Field(min_length=1, max_length=2000)
    answer_en: str = Field(min_length=1, max_length=2000)


class EscalationPolicy(Contract):
    keywords: list[str] = Field(default_factory=list, max_length=100)
    pause_automation: bool = True


class VoiceConfig(Contract):
    booking_confirmation_mode: Literal['speech','keypad'] = 'speech'
    locale: Locale = 'bg-BG'
    telephony_provider: Literal['mock', 'twilio', 'asterisk'] = 'mock'
    stt_provider: Literal['mock', 'azure', 'faster_whisper'] = 'mock'
    tts_provider: Literal['mock', 'azure', 'piper', 'espeak_ng', 'bgtts38'] = 'mock'
    incoming_phone_number: str = ''
    voices: dict[Locale, str] = Field(default_factory=lambda: {'bg-BG': 'mock-bg', 'en-US': 'mock-en'})
    greetings: dict[Locale, str] = Field(default_factory=lambda: {
        'bg-BG': 'Здравейте! Как мога да Ви помогна?', 'en-US': 'Hello! How can I help you?'})
    call_timeout_seconds: int = Field(default=600, ge=30, le=3600)
    silence_timeout_seconds: int = Field(default=30, ge=5, le=120)
    turn_silence_ms: int = Field(default=600, ge=100, le=2000)
    max_utterance_seconds: int = Field(default=20, ge=1, le=30)
    max_latency_ms: int = Field(default=10000, ge=500, le=120000)
    max_concurrent_calls: int = Field(default=4, ge=1, le=32)
    human_escalation_number: str = ''
    recording: bool = False
    transcript_storage: bool = False
    transcript_retention_days: int = Field(default=7, ge=1, le=365)
    lawful_basis: Literal['none', 'consent', 'contract', 'legitimate_interests'] = 'none'
    privacy_notices: dict[Locale, str] = Field(default_factory=lambda: {
        'bg-BG': 'Този разговор използва автоматизиран асистент.',
        'en-US': 'This call uses an automated assistant.'})
    recording_notices: dict[Locale, str] = Field(default_factory=lambda: {
        'bg-BG': 'С Вашето съгласие ще съхраняваме аудио и текстови откъси според настроения срок.',
        'en-US': 'With your consent, audio and transcript excerpts will be stored for the configured retention period.'})

    @field_validator('voices', 'greetings', 'privacy_notices', 'recording_notices')
    @classmethod
    def both_languages(cls, value):
        if set(value) != set(LOCALES) or any(not text.strip() or len(text) > 2000 for text in value.values()):
            raise ValueError('both_locales_required')
        return value

    @field_validator('incoming_phone_number', 'human_escalation_number')
    @classmethod
    def phone(cls, value):
        import re
        if value and not re.fullmatch(r'\+[1-9]\d{7,14}', value):
            raise ValueError('invalid_phone')
        return value


class AssistantConfig(Contract):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=1000)
    instructions: str = Field(default='', max_length=8000)
    faq_entries: list[FAQEntry] = Field(default_factory=list, max_length=100)
    enabled_channels: list[Channel] = Field(default_factory=lambda: list(Channel))
    supported_locales: list[Locale] = Field(default_factory=lambda: list(LOCALES))
    default_locale: Locale = 'bg-BG'
    llm_provider: str = 'mock'
    voice_provider: str = 'mock'
    llm_settings: dict[str, Any] = Field(default_factory=lambda: {'temperature': 0.2, 'max_tokens': 1024})
    voice_settings: VoiceConfig = Field(default_factory=VoiceConfig)
    assigned_agents: list[str] = Field(default_factory=lambda: ['receptionist', 'executor'])
    allowed_tools: list[str] = Field(default_factory=lambda: [
        'CheckAvailability', 'CreateAppointment', 'RescheduleAppointment',
        'CancelAppointment', 'SendMessage', 'CreateFollowUpTask', 'EscalateToHuman'])
    escalation_rules: EscalationPolicy = Field(default_factory=EscalationPolicy)
    status: Literal['active', 'disabled'] = 'active'
    booking_duration_minutes: int = Field(default=30, ge=5, le=480)
    public_knowledge_only: bool = False

    @field_validator('supported_locales')
    @classmethod
    def bilingual(cls, value):
        if set(value) != set(LOCALES):
            raise ValueError('both_locales_required')
        return value


class Attachment(Contract):
    name: str = Field(max_length=200)
    media_type: str = Field(max_length=100)
    storage_key: str = Field(max_length=300)
    size: int = Field(ge=0, le=10_000_000)


class Message(Contract):
    id: str
    tenant_id: str
    assistant_id: str
    conversation_id: str
    channel: Channel
    provider: str = 'mock'
    external_id: str = Field(min_length=1, max_length=200)
    sender: str = Field(max_length=200)
    recipient: str = Field(max_length=200)
    content: str = Field(max_length=10000)
    type: Literal['text', 'audio', 'email', 'template'] = 'text'
    attachments: list[Attachment] = Field(default_factory=list)
    locale: Locale
    timestamp: datetime
    status: str = 'received'
    metadata: dict[str, Any] = Field(default_factory=dict)
    external_message_id: str | None = None
    sender_id: str | None = None
    recipient_id: str | None = None
    direction: Literal['inbound', 'outbound'] = 'inbound'
    content_type: str | None = None
    detected_locale: Locale | None = None
    active_locale: Locale | None = None
    delivery_status: str | None = None
    correlation_id: str = ''

    def model_post_init(self, context):
        self.external_message_id = self.external_message_id or self.external_id
        self.sender_id, self.recipient_id = self.sender_id or self.sender, self.recipient_id or self.recipient
        self.content_type, self.active_locale = self.content_type or self.type, self.active_locale or self.locale
        self.delivery_status = self.delivery_status or self.status


class NormalizedInbound(Contract):
    external_message_id: str = Field(min_length=1, max_length=200)
    sender_id: str = Field(min_length=1, max_length=200)
    recipient_id: str = Field(min_length=1, max_length=200)
    content: str = Field(default='', max_length=10000)
    content_type: Literal['text', 'email', 'attachment', 'status', 'template_status'] = 'text'
    timestamp: datetime
    explicit_locale: Locale | None = None
    attachments: list[dict] = Field(default_factory=list, max_length=10)
    metadata: dict = Field(default_factory=dict)

    @field_validator('timestamp')
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None: raise ValueError('timezone_required')
        return value


class Incoming(Contract):
    content: str = Field(min_length=1, max_length=10000)
    event_id: str = Field(min_length=1, max_length=300)
    locale: Locale | None = None
    tool: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    attachment_ids: list[str] = Field(default_factory=list, max_length=10)


class BookingInterpretationRequest(Contract):
    content: str = Field(max_length=10000)
    locale: Locale
    collecting_name: bool = False
    context: dict[str, Any] = Field(default_factory=dict)


class BookingIntent(Contract):
    intent: Literal['book', 'details', 'confirm', 'cancel', 'none'] = 'none'
    date_text: str | None = Field(default=None, max_length=100)
    day_text: str | None = Field(default=None, max_length=50)
    contact_name: str | None = Field(default=None, min_length=1, max_length=120)
    duration_minutes: int | None = Field(default=None, ge=5, le=480)


class BookingState(Contract):
    status: Literal['need_date', 'need_name', 'awaiting_confirmation', 'completed', 'unavailable', 'cancelled']
    reference_at: datetime
    timezone: str
    starts_at: str | None = None
    requested_day: str | None = None
    duration_minutes: int = Field(default=30, ge=5, le=480)
    contact_name: str | None = None
    approval_id: str | None = None
    locale: Locale


class AppointmentArgs(Contract):
    starts_at: datetime
    duration_minutes: int = Field(default=30, ge=5, le=480)
    contact_name: str = Field(min_length=1, max_length=120)

    @field_validator('starts_at')
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError('timezone_required')
        return value


class AppointmentId(Contract):
    appointment_id: str = Field(min_length=1, max_length=100)


class RescheduleArgs(AppointmentArgs):
    appointment_id: str = Field(min_length=1, max_length=100)


class SendArgs(Contract):
    channel: Channel
    recipient: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10000)


class FollowUpArgs(Contract):
    title: str = Field(min_length=1, max_length=200)
    due_at: datetime

    @field_validator('due_at')
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError('timezone_required')
        return value


class EscalationArgs(Contract):
    reason: str = Field(min_length=1, max_length=500)


class AvailabilityArgs(Contract):
    starts_at: datetime | None = None
    day: date | None = None
    duration_minutes: int = Field(default=30, ge=5, le=480)

    @field_validator('starts_at')
    @classmethod
    def aware(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError('timezone_required')
        return value

    @model_validator(mode='after')
    def one_target(self):
        if (self.starts_at is None) == (self.day is None): raise ValueError('Choose a day or a timestamp')
        return self


class Handoff(Contract):
    tenant_id: str
    conversation_id: str
    source_agent: str = 'receptionist'
    target_agent: str = 'executor'
    intent: str
    arguments: dict[str, Any]
    locale: Locale
    correlation_id: str
    max_steps: int = Field(default=4, ge=1, le=8)
    max_depth: int = Field(default=1, ge=1, le=2)
    tool_budget: int = Field(default=1, ge=1, le=3)
    assistant_id: str | None = None
    contact_id: str | None = None
    call_session_id: str | None = None
    tool_permissions: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    user_id: str
    role: str
    subject: str

    def require(self, permission: str) -> None:
        grants = {'admin': {'read', 'configure', 'execute', 'approve'},
                  'operator': {'read', 'execute', 'approve'}, 'viewer': {'read'}}
        if permission not in grants.get(self.role, set()):
            raise DomainError('forbidden', 403)


class DomainError(Exception):
    def __init__(self, code: str, status: int = 400):
        self.code, self.status = code, status
        super().__init__(code)


@dataclass(frozen=True)
class Capability:
    provider: str
    state: str
    locales: tuple[str, ...] = LOCALES
    features: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ('synthetic_only',)
    speech_validated: bool = False


class LLMProvider(Protocol):
    capability: Capability
    def reply(self, text: str, locale: Locale, instructions: str) -> str: ...
    def interpret_booking(self, request: BookingInterpretationRequest) -> BookingIntent: ...


class CalendarProvider(Protocol):
    def available(self, tenant_id: str, starts_at: str, minutes: int, exclude: str | None = None) -> bool: ...
    def day_slots(self, tenant_id: str, day: str, minutes: int, timezone: str, after: datetime) -> list[str]: ...
    def create(self, tenant_id: str, arguments: dict, conversation: dict, timezone: str) -> dict: ...
    def reschedule(self, tenant_id: str, appointment_id: str, arguments: dict) -> dict: ...
    def cancel(self, tenant_id: str, appointment_id: str) -> dict: ...


class SpeechToTextProvider(Protocol):
    capability: Capability
    def transcribe(self, sample: bytes, locale: Locale) -> str: ...


class TextToSpeechProvider(Protocol):
    capability: Capability
    def synthesize(self, text: str, locale: Locale) -> bytes: ...


class TelephonyProvider(Protocol):
    capability: Capability
    def start(self, call_id: str, locale: Locale) -> dict: ...
    def transfer(self, call_id: str, destination: str) -> dict: ...
    def terminate(self, call_id: str) -> dict: ...
    def verify_webhook(self, url: str, body: bytes, signature: str) -> bool: ...


class AudioFrame(Contract):
    sequence: int = Field(ge=0, le=100000000)
    utterance_id: str = Field(min_length=1, max_length=100)
    payload: str = Field(max_length=44000)
    encoding: Literal['fixture_utf8', 'pcm16', 'mulaw'] = 'fixture_utf8'
    sample_rate: Literal[8000, 16000] = 8000
    final: bool = False


class RecognitionResult(Contract):
    text: str = Field(max_length=10000)
    utterance_id: str = Field(min_length=1, max_length=100)
    final: bool = True
    locale: Locale | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)


class KeypadInput(Contract):
    digit: Literal['0','1']
    utterance_id: str = Field(min_length=1,max_length=100)
    received_at: datetime


class AudioTransport(Protocol):
    async def receive(self) -> dict: ...
    async def send_audio(self, payload: bytes, *, encoding: str, turn_id: str) -> None: ...
    async def clear(self) -> None: ...
    async def send_event(self, event: dict) -> None: ...
    async def close(self) -> None: ...


class LegacyEmailProvider(Protocol):
    capability: Capability
    def send(self, message: Message) -> dict: ...


class WhatsAppProvider(Protocol):
    capability: Capability
    def send(self, message: Message) -> dict: ...


class LegacySMSProvider(Protocol):
    capability: Capability
    def send(self, message: Message) -> dict: ...


def validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ValueError, KeyError):
        raise DomainError('invalid_timezone') from None
    return value
