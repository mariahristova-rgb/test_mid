"""Provider-independent SaaS contracts; monetary amounts are integer minor units."""
from datetime import datetime
from typing import Literal, Protocol
from pydantic import Field, StrictInt, field_validator, model_validator
from .domain import Contract, Locale, validate_timezone

UNITS = {'ai_messages': 'message', 'agent_executions': 'execution', 'tool_executions': 'execution',
    'voice_seconds': 'second', 'stt_seconds': 'second', 'tts_characters': 'character', 'sms_segments': 'segment',
    'whatsapp_messages': 'message', 'email_messages': 'message', 'llm_input_tokens': 'token', 'llm_output_tokens': 'token',
    'storage_bytes': 'byte'}
RESOURCES = {'assistants': 'assistants', 'agents': 'agents', 'users': 'users', 'channel_connections': 'connections'}


class Limit(Contract):
    maximum: StrictInt = Field(ge=0)
    mode: Literal['hard', 'soft'] = 'hard'
    warning_percent: StrictInt = Field(default=80, ge=1, le=100)
    overage_policy: Literal['block', 'warn', 'meter'] = 'block'
    overage_minor_per_unit: StrictInt = Field(default=0, ge=0)

    @model_validator(mode='after')
    def coherent_policy(self):
        if self.mode == 'hard' and self.overage_policy != 'block': raise ValueError('A hard limit must block overage')
        return self


class SubscriptionPlan(Contract):
    id: str = Field(pattern=r'^[a-z0-9_-]{1,80}$')
    name_bg: str = Field(min_length=1, max_length=120)
    name_en: str = Field(min_length=1, max_length=120)
    currency: Literal['EUR', 'USD', 'BGN'] = 'EUR'
    minor_digits: Literal[2] = 2
    monthly_minor: StrictInt = Field(default=0, ge=0)
    annual_minor: StrictInt = Field(default=0, ge=0)
    trial_days: StrictInt = Field(default=0, ge=0, le=90)
    grace_days: StrictInt = Field(default=3, ge=0, le=30)
    rank: StrictInt = Field(default=0, ge=0)
    retention_days: StrictInt = Field(default=30, ge=1, le=3650)
    monthly_voice_minutes: StrictInt | None = Field(default=None, ge=0)
    limits: dict[str, Limit] = Field(default_factory=dict)
    connector_limit: StrictInt | None = Field(default=None, ge=0)
    connector_providers: list[Literal['google','outlook','calendly','hubspot']] | None = None
    enabled: bool = True
    mock_only: bool = True

    @field_validator('limits')
    @classmethod
    def known_categories(cls, values):
        if set(values) - (set(UNITS) | set(RESOURCES.values())): raise ValueError('Unknown entitlement')
        return values

    @model_validator(mode='after')
    def voice_minute_limit(self):
        if self.monthly_voice_minutes is not None:
            seconds = self.monthly_voice_minutes * 60
            if 'voice_seconds' in self.limits and self.limits['voice_seconds'].maximum != seconds: raise ValueError('Conflicting voice limits')
            self.limits.setdefault('voice_seconds', Limit(maximum=seconds))
        return self


class RegisterOrganization(Contract):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=200)
    default_locale: Locale
    timezone: str
    plan_id: str
    interval: Literal['monthly', 'annual'] = 'monthly'
    event_id: str = Field(min_length=1, max_length=100)

    @field_validator('timezone')
    @classmethod
    def zone(cls, value): return validate_timezone(value)


class UsageEvent(Contract):
    resource_id: str = Field(min_length=1, max_length=200)
    category: str
    quantity: StrictInt = Field(ge=0)
    unit: str
    provider: str = Field(min_length=1, max_length=80)
    timestamp: datetime
    correlation_id: str = Field(default='', max_length=100)
    idempotency_key: str = Field(min_length=1, max_length=200)
    billable: bool = False

    @field_validator('timestamp')
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None: raise ValueError('timezone_required')
        return value


class PaymentEvent(Contract):
    event_id: str = Field(min_length=1, max_length=200)
    customer_id: str
    invoice_id: str
    kind: Literal['invoice_paid', 'payment_failed']
    amount_minor: StrictInt = Field(ge=0)
    currency: str
    timestamp: datetime

    @field_validator('timestamp')
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None: raise ValueError('timezone_required')
        return value


class PaymentProvider(Protocol):
    def create_customer(self, tenant_id: str) -> dict: ...
    def create_checkout(self, invoice: dict, key: str) -> dict: ...
    def create_subscription(self, customer: dict, plan: dict, interval: str) -> dict: ...
    def update_subscription(self, subscription: dict, changes: dict) -> dict: ...
    def cancel_subscription(self, subscription: dict) -> dict: ...
    def retrieve_invoice(self, invoice: dict) -> dict: ...
    def payment_status(self, invoice: dict) -> str: ...
    def verify_webhook(self, raw: bytes, signature: str, secret: str) -> PaymentEvent: ...
