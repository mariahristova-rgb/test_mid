"""Authenticated control plane and signed provider event ingress."""
import hmac
from datetime import datetime, date, time, timedelta
from typing import Literal
from fastapi import Depends, Request, Query
from fastapi.responses import PlainTextResponse
from pydantic import Field, SecretStr
from .domain import Contract, Principal, Locale, DomainError
from .store import event_key
from .messaging import NOTIFICATION_KEYS


class MessagingConnection(Contract):
    assistant_id: str = 'default'
    channel: Literal['email', 'whatsapp', 'sms', 'web_chat']
    provider: Literal['mock', 'smtp', 'meta', 'twilio'] = 'mock'
    sender_id: str = Field(max_length=200)
    public_origin: str = Field(default='', max_length=300)
    enable_live: bool = False
    email_draft_required: bool = True
    max_event_age_seconds: int = Field(default=604800, ge=60, le=2592000)
    rate_per_minute: int = Field(default=30, ge=1, le=300)
    waba_id: str = Field(default='', max_length=100)
    phone_number_id: str = Field(default='', max_length=100)
    api_version: str = Field(default='', pattern=r'^(v\d+\.\d+)?$')
    account_sid: str = Field(default='', max_length=100)
    smtp_host: str = Field(default='', max_length=200)
    smtp_port: Literal[465, 587] = 465
    smtp_username: str = Field(default='', max_length=200)
    webhook_secret: SecretStr = SecretStr('')
    app_secret: SecretStr = SecretStr('')
    verify_token: SecretStr = SecretStr('')
    access_token: SecretStr = SecretStr('')
    auth_token: SecretStr = SecretStr('')
    smtp_password: SecretStr = SecretStr('')


class HumanControl(Contract):
    action: Literal['takeover', 'resume', 'close']
    confirmed: Literal[True]


class Confirm(Contract):
    confirmed: Literal[True]


class ConnectionState(Contract):
    enabled: bool
    confirmed: Literal[True]


class AttachmentUpload(Contract):
    name: str = Field(min_length=1, max_length=200)
    media_type: str = Field(max_length=100)
    data_base64: str = Field(max_length=2_700_000)


class LinkContacts(Contract):
    first_id: str
    second_id: str
    evidence: str = Field(min_length=1, max_length=300)
    confirmed: Literal[True]


class Notification(Contract):
    conversation_id: str
    template_key: str = Field(max_length=50)
    variables: dict[str, str] = Field(default_factory=dict)
    due_at: datetime
    event_id: str = Field(min_length=1, max_length=200)
    confirmed: Literal[True]


class HumanReply(Contract):
    content: str = Field(min_length=1, max_length=10000)
    event_id: str = Field(min_length=1, max_length=200)
    confirmed: Literal[True]


class Consent(Contract):
    sms_consent: bool = False
    whatsapp_consent: bool = False
    evidence: str = Field(min_length=1, max_length=300)
    confirmed: Literal[True]


class ProviderTemplate(Contract):
    connection_id: str
    template_key: Literal['appointment_created', 'appointment_rescheduled', 'appointment_cancelled', 'reminder', 'follow_up', 'human_escalation']
    provider_name: str = Field(pattern=r'^[a-z0-9_]{1,100}$')
    locale: Locale
    mock_approved: bool = False


def register_messaging(app, gateway, actor):
    store = gateway.store

    @app.post('/api/messaging/connections', status_code=201)
    def configure(config: MessagingConnection, principal: Principal = Depends(actor)):
        names = ('webhook_secret', 'app_secret', 'verify_token', 'access_token', 'auth_token', 'smtp_password')
        credentials = {name: getattr(config, name).get_secret_value() for name in names}
        return gateway.configure(principal, config.model_dump(exclude=set(names)), credentials)

    @app.get('/api/messaging/connections')
    def connections(principal: Principal = Depends(actor)):
        return [row for row in store.list('channel_connections', principal.tenant_id) if 'credential_names' in row]

    @app.put('/api/messaging/connections/{id}/state')
    def connection_state(id: str, config: ConnectionState, principal: Principal = Depends(actor)):
        principal.require('configure')
        connection = store.get('channel_connections', principal.tenant_id, id)
        if 'credential_names' not in connection: raise DomainError('invalid_input', 422)
        result = store.update('channel_connections', principal.tenant_id, id, {'enabled': config.enabled})
        store.audit(principal, 'messaging:enabled' if config.enabled else 'messaging:disabled', resource_id=id)
        return result

    @app.post('/webhooks/messaging/{tenant_id}/{connection_id}', status_code=202)
    async def ingress(tenant_id: str, connection_id: str, request: Request):
        if request.query_params: raise DomainError('invalid_input', 422)
        return gateway.ingest(tenant_id, connection_id, await request.body(), dict(request.headers), webhook_path=request.url.path)

    @app.post('/webhooks/messaging/{tenant_id}/{connection_id}/status/{message_id}', status_code=202)
    async def status(tenant_id: str, connection_id: str, message_id: str, request: Request):
        if request.query_params: raise DomainError('invalid_input', 422)
        return gateway.ingest(tenant_id, connection_id, await request.body(), dict(request.headers), webhook_path=request.url.path, message_id=message_id)

    @app.get('/webhooks/messaging/{tenant_id}/{connection_id}')
    def challenge(tenant_id: str, connection_id: str, request: Request):
        connection = store.get('channel_connections', tenant_id, connection_id)
        gateway.principal(connection)
        params = request.query_params
        if connection['provider'] != 'meta' or params.get('hub.mode') != 'subscribe' or not hmac.compare_digest(params.get('hub.verify_token', ''), gateway.credentials(connection)['verify_token']):
            raise DomainError('invalid_signature', 401)
        value = params.get('hub.challenge', '')
        if len(value) > 200: raise DomainError('invalid_input', 422)
        return PlainTextResponse(value)

    @app.post('/api/messaging/run')
    def run(config: Confirm, principal: Principal = Depends(actor)):
        return gateway.run(principal)

    @app.post('/api/conversations/{id}/control')
    def control(id: str, config: HumanControl, principal: Principal = Depends(actor)):
        return gateway.human_control(principal, id, config.action)

    @app.post('/api/conversations/{id}/human-reply')
    def reply(id: str, config: HumanReply, principal: Principal = Depends(actor)):
        return gateway.human_reply(principal, id, config.content, config.event_id)

    @app.post('/api/messages/{id}/approve-draft')
    def approve(id: str, config: Confirm, principal: Principal = Depends(actor)):
        return gateway.approve_draft(principal, id)

    @app.post('/api/contacts/{id}/consent')
    def consent(id: str, config: Consent, principal: Principal = Depends(actor)):
        principal.require('approve')
        store.get('contacts', principal.tenant_id, id)
        result = store.update('contacts', principal.tenant_id, id, {**config.model_dump(exclude={'confirmed'}), 'consent_recorded_by': principal.user_id, 'consent_at': gateway.clock().isoformat()})
        store.audit(principal, 'contact:consent', resource_id=id)
        return result

    @app.get('/api/messaging/templates')
    def templates(principal: Principal = Depends(actor)):
        return store.list('approved_templates', principal.tenant_id)

    @app.post('/api/messaging/templates', status_code=201)
    def template(config: ProviderTemplate, principal: Principal = Depends(actor)):
        principal.require('configure')
        connection = store.get('channel_connections', principal.tenant_id, config.connection_id)
        if connection['channel'] != 'whatsapp' or config.mock_approved and connection['provider'] != 'mock': raise DomainError('forbidden', 403)
        row = {**config.model_dump(exclude={'mock_approved'}), 'status': 'approved' if config.mock_approved else 'pending', 'verified_by': 'mock_fixture' if config.mock_approved else None}
        return store.add('approved_templates', principal.tenant_id, row, external_key=event_key(connection['id'], config.template_key + ':' + config.locale))

    @app.post('/api/conversations/{id}/redact')
    def redact(id: str, config: Confirm, principal: Principal = Depends(actor)):
        return gateway.delete_content(principal, id)

    @app.post('/api/messaging/retention')
    def retention(config: Confirm, principal: Principal = Depends(actor)):
        return gateway.purge_expired(principal)

    @app.post('/api/jobs/{id}/retry')
    def retry(id: str, config: Confirm, principal: Principal = Depends(actor)):
        principal.require('approve')
        job = store.get('jobs', principal.tenant_id, id)
        safe = ('unconfigured', 'template_required', 'consent_required', 'disabled', 'forbidden', 'rate_limited', 'upgrade_required', 'subscription_required')
        if job['status'] != 'dead_letter' or job.get('kind') != 'outbound_message' or job.get('error_code') not in safe:
            raise DomainError('forbidden', 403)
        result = store.update('jobs', principal.tenant_id, id, {'status': 'pending', 'due_at': gateway.clock().isoformat()})
        store.audit(principal, 'job:retry_requested', resource_id=id)
        return result

    @app.post('/api/conversations/{id}/attachments', status_code=201)
    def upload(id: str, config: AttachmentUpload, principal: Principal = Depends(actor)):
        principal.require('execute')
        with store.transaction():
            return gateway.attachments.put(principal.tenant_id, id, config.model_dump())

    @app.post('/api/contacts/link', status_code=201)
    def link(config: LinkContacts, principal: Principal = Depends(actor)):
        principal.require('approve')
        store.get('contacts', principal.tenant_id, config.first_id)
        store.get('contacts', principal.tenant_id, config.second_id)
        if config.first_id == config.second_id: raise DomainError('invalid_input', 422)
        key = event_key('contact_link', ':'.join(sorted([config.first_id, config.second_id])))
        existing = store.find('contact_links', principal.tenant_id, key)
        if existing: return existing
        result = store.add('contact_links', principal.tenant_id, {**config.model_dump(exclude={'confirmed'}), 'authorized_by': principal.user_id}, external_key=key)
        store.audit(principal, 'contact:linked', resource_id=result['id'])
        return result

    @app.post('/api/notifications', status_code=201)
    def notification(config: Notification, principal: Principal = Depends(actor)):
        return gateway.schedule_notification(principal, config.conversation_id, config.template_key, config.variables, config.due_at, config.event_id)

    @app.get('/api/inbox')
    def inbox(channel: str | None = None, assistant_id: str | None = None, status: str | None = None, locale: str | None = None,
              from_date: datetime | None = None, to_date: datetime | None = None,
              limit: int | None = Query(None,ge=1,le=100), cursor: int | None = Query(None,ge=0), conversation_id: str | None = None,
              local_day: date | None = None,
              principal: Principal = Depends(actor)):
        if any(d and d.tzinfo is None for d in (from_date, to_date)): raise DomainError('timezone_required', 422)
        if cursor is not None and limit is None: raise DomainError('invalid_input',422)
        if local_day:
            from zoneinfo import ZoneInfo
            if from_date or to_date: raise DomainError('invalid_input',422)
            zone=ZoneInfo(store.tenant(principal.tenant_id)['timezone'])
            from_date=datetime.combine(local_day,time.min,tzinfo=zone)
            to_date=datetime.combine(local_day+timedelta(days=1),time.min,tzinfo=zone)
        return store.inbox(principal.tenant_id, filters={'channel':channel,'assistant_id':assistant_id,'status':status,'active_locale':locale},
            from_date=from_date,to_date=to_date,limit=limit,cursor=cursor,identity=conversation_id,to_date_exclusive=bool(local_day))
