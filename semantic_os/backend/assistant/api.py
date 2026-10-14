"""FastAPI composition root. Mock defaults with explicitly gated provider infrastructure."""
from __future__ import annotations
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import os
from typing import Literal
from fastapi import FastAPI, Request, Depends, HTTPException, WebSocket
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import Field, ValidationError, SecretStr
from .domain import (Contract, AssistantConfig, Incoming, Locale, Channel, Principal,
                     DomainError, Message, LOCALES, validate_timezone)
from .language import tr, parse_date, parse_duration
from .orchestration import Orchestrator
from .providers import ProviderRegistry, e164
from .security import IdentityService, TenantSecretStore
from .store import Store, uid, now, event_key
from .voice import VoiceSessionManager
from .voice_gateway import TelephonyGateway
from .voice_stream import VoiceRuntime, WebSocketAudioTransport
from .live_voice import stream_twiml
from .jobs import ReminderQueue
from .messaging import MessagingGateway
from .messaging_api import register_messaging
from .billing import BillingService
from .saas_api import register_saas


class DemoLogin(Contract):
    username: str = Field(min_length=1,max_length=80)
    password: SecretStr = Field(min_length=1,max_length=200)
from .privacy import PrivacyService
from .backup import BackupManager
from .observability import Operations, correlation_id
from ..api.rate_limit import IpRateLimiter


class ConversationCreate(Contract):
    assistant_id: str = 'default'
    channel: Channel = Channel.WEB_CHAT
    contact_id: str | None = None


class Confirmation(Contract):
    confirmed: Literal[True]


class AgentUpdate(Contract):
    enabled: bool = True
    allowed_tools: list[str]
    instructions: str = Field(default='', max_length=8000)
    supported_locales: list[Locale] = Field(default_factory=lambda: list(LOCALES))


class SettingsUpdate(Contract):
    default_locale: Locale
    timezone: str
    usage_limit: int = Field(ge=1, le=1_000_000)
    retention_days: int = Field(ge=1, le=3650)
    recording_enabled: bool = False
    transcripts_enabled: bool = False
    notice_acknowledged: bool = False


class ContactCreate(Contract):
    name: str = Field(min_length=1, max_length=120)
    address: str = Field(min_length=1, max_length=200)
    preferred_locale: Locale = 'bg-BG'
    sms_opt_out: bool = False


class CallCreate(Contract):
    assistant_id: str = 'default'
    locale: Locale | None = None
    recording: bool = False
    transcript_storage: bool = False
    consent_given: bool = False
    caller: str = Field(default='anonymous', max_length=40)


class CallEvent(Contract):
    action: Literal['speak', 'barge_in', 'finish_speaking', 'language', 'transcript', 'transfer', 'terminate']
    locale: Locale | None = None
    text: str = Field(default='', max_length=10000)
    destination: str = Field(default='human', max_length=200)
    event_id: str = Field(min_length=1, max_length=200)
    utterance_id: str | None = Field(default=None, max_length=100)
    final: bool = True
    confirmed: bool = False
    tool: str | None = None
    arguments: dict = Field(default_factory=dict)


class TelephonyConnectionCreate(Contract):
    assistant_id: str = 'default'
    provider: Literal['mock', 'twilio'] = 'mock'
    phone_number: str = Field(max_length=30)
    public_origin: str = Field(default='', max_length=300)
    account_sid: str = Field(default='', max_length=100)
    speech_resource: str = Field(default='', max_length=100)
    speech_region: str = Field(default='', max_length=100)
    enable_live: bool = False
    webhook_secret: SecretStr = Field(default=SecretStr(''))
    auth_token: SecretStr = Field(default=SecretStr(''))
    speech_key: SecretStr = Field(default=SecretStr(''))


class ConnectionCreate(Contract):
    assistant_id: str = 'default'
    channel: Channel
    provider: Literal['mock'] = 'mock'
    secret: str = Field(min_length=32, max_length=1000)


class DateParse(Contract):
    value: str = Field(min_length=1, max_length=100)
    locale: Locale


class StatusCallback(Contract):
    event_id: str = Field(min_length=1, max_length=200)
    external_id: str = Field(min_length=1, max_length=200)
    status: Literal['sent', 'delivered', 'failed', 'read']


class TemplateUpdate(Contract):
    body: str = Field(min_length=1, max_length=10000)


class UserConfig(Contract):
    subject: str = Field(min_length=1, max_length=200)
    role: Literal['admin', 'operator', 'viewer'] = 'viewer'
    enabled: bool = True
    preferred_locale: Locale = 'en-US'


class ProfileConfig(Contract):
    ui_locale: Locale


def ui_locale(request):
    locale = request.headers.get('x-ui-locale', '')
    return locale if locale in LOCALES else 'en-US'


def create_app(*, store=None, providers=None, demo_enabled=None, demo_token=None, encryption_key=None, verifier=None, clock=None, platform_subjects=None, backup_key=None, backup_directory=None, connector_fixtures=False, customer_oauth_options=None):
    store = store or Store(os.getenv('ASSISTANT_DATABASE', '.assistant-data/assistant.sqlite3'))
    if providers is None:
        providers = ProviderRegistry()
        from .self_hosted import configure_environment
        configure_environment(providers)
        from .self_hosted import configure_speech
        configure_speech(providers)
    demo_enabled = demo_enabled if demo_enabled is not None else os.getenv('ASSISTANT_DEMO', 'false').lower() == 'true'
    from .self_hosted import deployment_secret
    owner_credentials=None
    owner_login_enabled=os.getenv('ASSISTANT_GOOGLE_LOGIN_ENABLED')=='true'
    if owner_login_enabled:
        if demo_enabled or os.getenv('AUTH0_DOMAIN'):raise RuntimeError('Choose one verified identity provider; Google owner login cannot use demo authentication')
        if os.getenv('ASSISTANT_GOOGLE_LOGIN_GCP_PROJECT'):
            from .google_secret_manager import owner_oauth_credentials
            owner_credentials=owner_oauth_credentials(os.environ['ASSISTANT_GOOGLE_LOGIN_GCP_PROJECT'],os.getenv('ASSISTANT_GOOGLE_LOGIN_BUNDLE','primary'))
        else:owner_credentials=(deployment_secret('ASSISTANT_GOOGLE_LOGIN_CLIENT_ID'),deployment_secret('ASSISTANT_GOOGLE_LOGIN_CLIENT_SECRET'))
        if not owner_credentials[1]:raise RuntimeError('Owner OAuth client secret is required')
        if verifier is None:
            from .google_owner_login import GoogleOwnerVerifier
            verifier=GoogleOwnerVerifier(owner_credentials[0])
    demo_token = demo_token if demo_token is not None else deployment_secret('ASSISTANT_DEMO_TOKEN')
    if verifier is None and os.getenv('AUTH0_DOMAIN') and os.getenv('AUTH0_AUDIENCE'):
        from ..api.auth0_auth import Auth0Verifier
        verifier = Auth0Verifier(os.environ['AUTH0_DOMAIN'], os.environ['AUTH0_AUDIENCE'])
    identity = IdentityService(store, demo_enabled=demo_enabled, demo_token=demo_token, verifier=verifier)
    demo_login_password = deployment_secret('ASSISTANT_DEMO_LOGIN_PASSWORD') if demo_enabled and os.getenv('ASSISTANT_DEMO_LOGIN_ENABLED')=='true' else ''
    if demo_enabled:
        store.seed()
    secrets = TenantSecretStore(store, encryption_key if encryption_key is not None else deployment_secret('ASSISTANT_ENCRYPTION_KEY'))
    orchestrator = Orchestrator(store, providers, clock=clock)
    voice = VoiceSessionManager(store, providers, orchestrator)
    gateway = TelephonyGateway(store, secrets, voice)
    voice_runtime = VoiceRuntime(voice)
    jobs = ReminderQueue(store, orchestrator)
    messaging = MessagingGateway(store, secrets, orchestrator)
    store.operations = Operations()
    billing = BillingService(store, secrets, orchestrator.clock, demo=demo_enabled)
    privacy = PrivacyService(store, messaging, orchestrator.clock)
    backups = BackupManager(store, backup_directory or os.getenv('ASSISTANT_BACKUP_DIRECTORY', 'artifacts/backups'),
        backup_key if backup_key is not None else os.getenv('ASSISTANT_BACKUP_ENCRYPTION_KEY', ''),
        retention_days=int(os.getenv('ASSISTANT_BACKUP_RETENTION_DAYS', '7')),
        rpo_seconds=int(os.getenv('ASSISTANT_RPO_SECONDS', '86400')), rto_seconds=int(os.getenv('ASSISTANT_RTO_SECONDS', '3600')))
    platform_subjects = set(platform_subjects if platform_subjects is not None else filter(None, os.getenv('ASSISTANT_PLATFORM_ADMIN_SUBJECTS', '').split(',')))

    @asynccontextmanager
    async def lifespan(app):
        import asyncio
        from time import monotonic
        last_backup = 0.0
        if os.getenv('SELF_HOSTED_VOICE_ENABLED')=='true':
            await asyncio.to_thread(voice.warm_local_prompts)
        async def maintenance():
            nonlocal last_backup
            store.operations.worker.update(status='running', messaging_enabled=os.getenv('ASSISTANT_MESSAGING_WORKER_ENABLED') == 'true',
                backup_enabled=os.getenv('ASSISTANT_BACKUP_ENABLED') == 'true', voice_cleanup_enabled=True)
            while True:
                await asyncio.sleep(15)
                try:
                    store.operations.worker['inflight'] = 1
                    await voice_runtime.threaded(voice.expire_idle_calls)
                    await voice_runtime.threaded(app.state.widget.purge)
                    await asyncio.to_thread(app.state.concierge.worker)
                    await asyncio.to_thread(app.state.inbox_queue.purge)
                    await asyncio.to_thread(app.state.customer_workspace.purge)
                    if app.state.owner_login:await asyncio.to_thread(app.state.owner_login.purge)
                    if os.getenv('ASSISTANT_MESSAGING_WORKER_ENABLED') == 'true':
                        await voice_runtime.threaded(messaging.worker_tick)
                    if os.getenv('ASSISTANT_BACKUP_ENABLED') == 'true' and monotonic() - last_backup >= int(os.getenv('ASSISTANT_BACKUP_INTERVAL_SECONDS', '86400')):
                        await voice_runtime.threaded(backups.create)
                        last_backup = monotonic()
                        store.operations.worker['last_backup_at'] = orchestrator.clock().isoformat()
                    store.operations.worker.update(last_tick_at=orchestrator.clock().isoformat(), last_error=None)
                except Exception:
                    store.operations.worker['last_error'] = 'worker_failed'
                    store.operations.observe('background_job', error='worker_failed')
                finally: store.operations.worker['inflight'] = 0
        ari_bridge, ari_job = None, None
        if os.getenv('SELF_HOSTED_VOICE_ENABLED') == 'true':
            from .self_hosted import ari_settings
            from .asterisk import ARIBridge
            if not all((providers.local_stt, providers.local_tts, providers.asterisk, providers.qwen_settings)):
                raise DomainError('unconfigured', 503)
            ari_bridge = ARIBridge(ari_settings(), voice, voice_runtime)
            app.state.ari_bridge = ari_bridge
            async def ari_supervisor():
                try:
                    store.operations.worker['ari_status'] = 'connecting'
                    await ari_bridge.run()
                except asyncio.CancelledError: raise
                except Exception:
                    store.operations.worker['ari_status'] = 'failed'
                    store.operations.observe('ari_service', ari_bridge.settings.tenant_id, error='provider_error')
                finally: await ari_bridge.close()
            ari_job = asyncio.create_task(ari_supervisor())
        job = asyncio.create_task(maintenance())
        try:
            yield
        finally:
            job.cancel()
            await asyncio.gather(job, return_exceptions=True)
            if ari_job:
                ari_job.cancel()
                await asyncio.gather(ari_job, return_exceptions=True)
            store.operations.worker['status'] = 'draining'
            await asyncio.to_thread(voice_runtime.shutdown)
            store.operations.worker['status'] = 'stopped'
            store.close()

    strict = os.getenv('ASSISTANT_ENV') in ('production', 'staging')
    app = FastAPI(title='Multi-channel Assistant', version='0.2.0', lifespan=lifespan,
        docs_url=None if strict else '/docs', redoc_url=None if strict else '/redoc', openapi_url=None if strict else '/openapi.json')
    app.state.store, app.state.orchestrator, app.state.providers = store, orchestrator, providers
    app.state.voice, app.state.voice_gateway, app.state.voice_runtime = voice, gateway, voice_runtime
    app.state.messaging = messaging
    app.state.billing, app.state.operations, app.state.backups, app.state.privacy = billing, store.operations, backups, privacy
    from .google_workspace import GoogleWorkspace
    from .concierge import Concierge
    app.state.google=GoogleWorkspace(store,secrets,orchestrator.clock,development=demo_enabled and not strict)
    app.state.concierge=Concierge(store,orchestrator,app.state.google,secrets,public_origin=os.getenv('WIDGET_PUBLIC_ORIGIN',''))
    ui_origins=[os.getenv('ASSISTANT_UI_ORIGIN', 'http://127.0.0.1:3000')]
    if demo_login_password:
        ui_origins=list(dict.fromkeys([*ui_origins,'http://127.0.0.1:3011','http://127.0.0.1:3017']))
    app.add_middleware(CORSMiddleware, allow_origins=ui_origins,
                       allow_methods=['GET', 'POST', 'PUT', 'OPTIONS'],
                       allow_headers=['Authorization', 'Content-Type', 'X-Tenant-ID', 'X-UI-Locale'])
    limiter = IpRateLimiter()

    def error(request, code, status):
        return JSONResponse({'code': code, 'message': tr(ui_locale(request), code)}, status_code=status)

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        principal = getattr(request.state, 'principal', None)
        if principal:
            store.audit(principal, 'request:rejected', status=exc.code)
        return error(request, exc.code, exc.status)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return error(request, 'invalid_input', 422)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        code = {401: 'unauthorized', 403: 'forbidden', 404: 'not_found', 503: 'unconfigured'}.get(exc.status_code, 'invalid_input')
        return error(request, code, exc.status_code)

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        logging.getLogger('assistant').error(json.dumps({'event': 'request_failed', 'error_type': type(exc).__name__, 'correlation_id': getattr(request.state, 'correlation_id', '')}))
        return error(request, 'provider_error', 500)

    @app.middleware('http')
    async def safeguards(request, call_next):
        try:
            length = int(request.headers.get('content-length', '0'))
        except ValueError:
            return error(request, 'invalid_input', 400)
        limit = 6_000_000 if request.url.path.startswith('/webhooks/messaging/') or request.url.path.endswith('/attachments') else 128_000
        if length > limit:
            return error(request, 'invalid_input', 413)
        if request.method in ('POST', 'PUT'):
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > limit:
                    return error(request, 'invalid_input', 413)
                chunks.append(chunk)
            request._body = b''.join(chunks)
        if request.url.path != '/health/live':
            decision = limiter.check(request)
            if not decision.allowed:
                return error(request, 'rate_limited', 429)
        response = await call_next(request)
        response.headers.update({'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store',
                                 'X-Correlation-ID': correlation_id.get() or uid(), 'Referrer-Policy': 'no-referrer',
                                 'X-Frame-Options': 'DENY', 'Permissions-Policy': 'camera=(), geolocation=()'})
        return response

    @app.middleware('http')
    async def instrumentation(request, call_next):
        from time import monotonic
        start = monotonic()
        correlation = uid()
        request.state.correlation_id = correlation
        token = correlation_id.set(correlation)
        try:
            response = await call_next(request)
            principal = getattr(request.state, 'principal', None)
            tenant = principal.tenant_id if principal else ''
            store.operations.observe('api_request', tenant, duration_ms=(monotonic() - start) * 1000,
                error='http_error' if response.status_code >= 400 else None)
            response.headers['X-Correlation-ID'] = correlation
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['Cache-Control'] = 'no-store'
            return response
        finally: correlation_id.reset(token)

    def actor(request: Request):
        principal = identity.authenticate(request.headers.get('authorization'), request.headers.get('x-tenant-id', 'demo'),
                                          request.client.host if request.client else '')
        principal.require('read')
        request.state.principal = principal
        recovery = request.url.path.startswith(('/api/billing', '/api/saas/onboarding', '/api/saas/access', '/api/usage', '/api/workspace/progress', '/api/workspace/usage', '/api/workspace/operations-targets', '/api/operations', '/api/privacy', '/api/profile'))
        billing.entitlements.access(principal.tenant_id, recovery=recovery)
        return principal

    @app.post('/api/demo/login')
    def demo_login(credentials: DemoLogin, request: Request):
        if not demo_login_password or not demo_enabled:
            raise DomainError('unconfigured',503)
        # Reuse the existing loopback/explicit private proxy boundary.
        identity.verify_identity('Bearer '+demo_token,request.client.host if request.client else '')
        import hmac
        username=os.getenv('ASSISTANT_DEMO_LOGIN_USERNAME','demo')
        if not (hmac.compare_digest(hashlib.sha256(credentials.username.encode()).digest(),hashlib.sha256(username.encode()).digest())
                and hmac.compare_digest(hashlib.sha256(credentials.password.get_secret_value().encode()).digest(),hashlib.sha256(demo_login_password.encode()).digest())):
            raise DomainError('unauthorized',401)
        tenant=os.getenv('ASSISTANT_DEMO_LOGIN_TENANT','demo')
        principal=identity.authenticate('Bearer '+demo_token,tenant,request.client.host if request.client else '')
        store.audit(principal,'demo:login')
        return {'access_token':demo_token,'tenant_id':tenant,'username':username}

    @app.get('/health/live')
    def health():
        return {'status': 'ok', 'providers': 'LIVE_UNVERIFIED' if providers.qwen_settings else 'MOCK'}

    @app.get('/health/ready')
    def ready():
        store.db.execute('SELECT 1')
        strict = os.getenv('ASSISTANT_ENV') in ('production', 'staging')
        if strict and (not verifier or not secrets.cipher or not billing.plans()): raise DomainError('unconfigured', 503)
        if strict and os.getenv('ASSISTANT_BACKUP_ENABLED') == 'true' and not backups.cipher: raise DomainError('unconfigured', 503)
        if strict and any(os.getenv(k) == 'true' for k in ('ASSISTANT_MESSAGING_WORKER_ENABLED', 'ASSISTANT_BACKUP_ENABLED')) and store.operations.worker['last_error']: raise DomainError('provider_error', 503)
        if os.getenv('SELF_HOSTED_VOICE_ENABLED') == 'true' and store.operations.worker.get('ari_status') != 'connected_unverified':
            raise DomainError('unconfigured', 503)
        return {'status': 'ready', 'authentication': 'configured' if demo_enabled or verifier else 'UNCONFIGURED'}

    @app.get('/api/bootstrap')
    def bootstrap(principal: Principal = Depends(actor)):
        tenant = store.tenant(principal.tenant_id)
        return {'tenant': tenant, 'user': {'id': principal.user_id, 'role': principal.role}, 'state': 'MOCK',
                'environment': os.getenv('ASSISTANT_ENV', 'development'), 'demo_enabled': demo_enabled,
                'platform_admin': principal.subject in platform_subjects,
                'counts': {name: store.count(name, principal.tenant_id) for name in ('assistants', 'conversations', 'appointments', 'call_sessions', 'usage_records')},
                'providers': providers.describe(), 'tools': orchestrator.tools.describe()}

    @app.post('/api/dates/parse')
    def parse(config: DateParse, principal: Principal = Depends(actor)):
        return {'iso': parse_date(config.value, config.locale, store.tenant(principal.tenant_id)['timezone']).isoformat()}

    @app.post('/api/dates/duration')
    def duration(config: DateParse, principal: Principal = Depends(actor)):
        return {'minutes': parse_duration(config.value, config.locale)}

    @app.get('/api/assistants')
    def assistants(principal: Principal = Depends(actor)):
        return [{**AssistantConfig.model_validate({key: value for key, value in record.items() if key not in ('id', 'tenant_id')}).model_dump(mode='json'),
                 'id': record['id'], 'tenant_id': record['tenant_id']} for record in store.list('assistants', principal.tenant_id)]

    def valid_config(config):
        providers.require(config.llm_provider, config.default_locale)
        if config.llm_provider == 'qwen':
            settings = config.llm_settings
            if (set(settings) - {'model','max_tokens','temperature'} or settings.get('model','Qwen3-4B') != providers.qwen_settings.model_name
                    or type(settings.get('max_tokens',256)) is not int or not 1 <= settings.get('max_tokens',256) <= 1024
                    or not isinstance(settings.get('temperature',.2),(int,float)) or not 0 <= settings.get('temperature',.2) <= 1):
                raise DomainError('invalid_input', 422)
        providers.require(config.voice_provider, config.default_locale)
        from .live_voice import AzureSpeechProvider
        if config.voice_settings.tts_provider in ('piper','espeak_ng','bgtts38'):
            if providers.local_tts is None: raise DomainError('unconfigured', 503)
            expected = {locale: (voice,) for locale, voice in providers.local_tts.voice_ids.items()}
        else:
            expected = {'bg-BG': ('mock-bg',), 'en-US': ('mock-en',)} if config.voice_settings.tts_provider == 'mock' else AzureSpeechProvider.VOICES
        if any(config.voice_settings.voices[locale] not in expected[locale] for locale in LOCALES):
            raise DomainError('unsupported_locale', 422)
        if set(config.assigned_agents) != {'receptionist', 'executor'} or not set(config.allowed_tools) <= set(orchestrator.tools_name_list):
            raise DomainError('invalid_input', 422)

    orchestrator.tools_name_list = [item['name'] for item in orchestrator.tools.describe()]

    from .ux import register_ux
    register_ux(app, store, providers, actor, valid_config)
    from .widget import register_widget,origin as widget_canonical_origin
    widget_origin=os.getenv('WIDGET_PUBLIC_ORIGIN','')
    if widget_origin and os.getenv('ASSISTANT_UI_ORIGIN') and widget_canonical_origin(widget_origin,local=demo_enabled and not strict)==widget_canonical_origin(os.environ['ASSISTANT_UI_ORIGIN'],local=demo_enabled and not strict):
        raise ValueError('Widget requires a dedicated origin separate from the application')
    widget_local_sites=os.getenv('WIDGET_DEMO_SITE_ORIGINS','').split(',') if demo_enabled and not strict else ()
    register_widget(app,store,orchestrator,app.state.ux,actor,public_origin=widget_origin,
        local_sites=tuple(site for site in widget_local_sites if site),
        demo_targets=json.loads(os.getenv('WIDGET_DEMO_SITE_TARGETS','{}')) if demo_enabled and not strict else None)
    from .concierge_api import register_concierge
    register_concierge(app,actor)
    app.state.owner_login=None
    if owner_login_enabled:
        from .google_owner_login import GoogleOwnerLogin,register_google_owner_login
        app.state.owner_login=GoogleOwnerLogin(store,secrets,orchestrator.clock,verifier,owner_credentials[1],os.environ['ASSISTANT_GOOGLE_LOGIN_TENANT'],os.environ['ASSISTANT_GOOGLE_LOGIN_REDIRECT_URI'])
        register_google_owner_login(app,app.state.owner_login)
    from .inbox_queue import register_inbox_queue
    register_inbox_queue(app,store,actor)

    @app.post('/api/assistants', status_code=201)
    def add_assistant(config: AssistantConfig, principal: Principal = Depends(actor)):
        principal.require('configure')
        valid_config(config)
        result = store.add('assistants', principal.tenant_id, config.model_dump(mode='json'))
        store.audit(principal, 'assistant:created', resource_id=result['id'])
        return result

    @app.put('/api/assistants/{id}')
    def edit_assistant(id: str, config: AssistantConfig, principal: Principal = Depends(actor)):
        principal.require('configure')
        valid_config(config)
        result = store.update('assistants', principal.tenant_id, id, config.model_dump(mode='json'))
        store.audit(principal, 'assistant:configured', resource_id=id)
        return result

    @app.get('/api/agents')
    def agents(principal: Principal = Depends(actor)):
        return store.list('agents', principal.tenant_id)

    @app.get('/api/profile')
    def profile(principal: Principal = Depends(actor)):
        user = store.get('users', principal.tenant_id, principal.user_id)
        return {'ui_locale': user['preferred_locale'], 'role': user['role']}

    @app.put('/api/profile')
    def profile_update(config: ProfileConfig, principal: Principal = Depends(actor)):
        store.update('users', principal.tenant_id, principal.user_id, {'preferred_locale': config.ui_locale})
        return {'ui_locale': config.ui_locale}

    @app.get('/api/users')
    def users(principal: Principal = Depends(actor)):
        principal.require('configure')
        return store.list('users', principal.tenant_id)

    @app.post('/api/users', status_code=201)
    def user(config: UserConfig, principal: Principal = Depends(actor)):
        principal.require('configure')
        result = store.add('users', principal.tenant_id, config.model_dump(), external_key=config.subject)
        store.audit(principal, 'membership:created', resource_id=result['id'])
        return result

    @app.put('/api/users/{id}')
    def user_edit(id: str, config: UserConfig, principal: Principal = Depends(actor)):
        principal.require('configure')
        with store.transaction():
            user = store.get('users', principal.tenant_id, id)
            if user['subject'] != config.subject:
                raise DomainError('invalid_input', 422)
            if user['role'] == 'admin' and (not config.enabled or config.role != 'admin'):
                if len([u for u in store.list('users', principal.tenant_id) if u['role'] == 'admin' and u['enabled']]) <= 1:
                    raise DomainError('conflict', 409)
            result = store.update('users', principal.tenant_id, id, config.model_dump())
            store.audit(principal, 'membership:configured', resource_id=id)
            return result

    @app.put('/api/agents/{id}')
    def agent(id: str, config: AgentUpdate, principal: Principal = Depends(actor)):
        principal.require('configure')
        if set(config.supported_locales) != set(LOCALES) or not set(config.allowed_tools) <= set(orchestrator.tools_name_list):
            raise DomainError('invalid_input', 422)
        result = store.update('agents', principal.tenant_id, id, config.model_dump())
        store.audit(principal, 'agent:configured', resource_id=id)
        return result

    @app.get('/api/conversations')
    def conversations(principal: Principal = Depends(actor)):
        return store.list('conversations', principal.tenant_id)

    @app.post('/api/conversations', status_code=201)
    def conversation(config: ConversationCreate, principal: Principal = Depends(actor)):
        return orchestrator.conversation(principal, config.assistant_id, config.channel.value, config.contact_id)

    @app.get('/api/conversations/{id}/messages')
    def history(id: str, principal: Principal = Depends(actor)):
        store.get('conversations', principal.tenant_id, id)
        return store.list('messages', principal.tenant_id, id)

    @app.get('/api/conversations/{id}/executions')
    def execution_history(id: str, principal: Principal = Depends(actor)):
        principal.require('configure')
        store.get('conversations', principal.tenant_id, id)
        return {'agents': store.list('agent_executions', principal.tenant_id, id),
                'tools': store.list('tool_executions', principal.tenant_id, id)}

    @app.post('/api/conversations/{id}/messages')
    def send(id: str, incoming: Incoming, principal: Principal = Depends(actor)):
        return orchestrator.inbound(principal, id, incoming)

    @app.post('/api/conversations/{id}/resume')
    def resume(id: str, config: Confirmation, principal: Principal = Depends(actor)):
        return messaging.human_control(principal, id, 'resume')

    @app.get('/api/approvals')
    def approvals(principal: Principal = Depends(actor)):
        return store.list('approvals', principal.tenant_id)

    @app.post('/api/approvals/{id}/confirm')
    def confirm(id: str, config: Confirmation, principal: Principal = Depends(actor)):
        return orchestrator.approve(principal, id)

    @app.get('/api/contacts')
    def contacts(principal: Principal = Depends(actor)):
        return store.list('contacts', principal.tenant_id)

    @app.post('/api/contacts', status_code=201)
    def contact(config: ContactCreate, principal: Principal = Depends(actor)):
        principal.require('execute')
        if config.address.startswith('+'):
            config.address = e164(config.address)
        return store.add('contacts', principal.tenant_id, config.model_dump(), external_key=config.address)

    @app.put('/api/contacts/{id}')
    def contact_edit(id: str, config: ContactCreate, principal: Principal = Depends(actor)):
        principal.require('execute')
        contact = store.get('contacts', principal.tenant_id, id)
        if config.address != contact['address']:
            raise DomainError('invalid_input', 422)
        return store.update('contacts', principal.tenant_id, id, config.model_dump())

    @app.get('/api/appointments')
    def appointments(principal: Principal = Depends(actor)):
        return store.list('appointments', principal.tenant_id)

    @app.get('/api/follow-up-tasks')
    def followups(principal: Principal = Depends(actor)):
        return store.list('follow_up_tasks', principal.tenant_id)

    @app.get('/api/calls')
    def calls(principal: Principal = Depends(actor)):
        return store.list('call_sessions', principal.tenant_id)

    @app.get('/api/calls/{id}/activity')
    def call_activity(id: str, principal: Principal = Depends(actor)):
        principal.require('configure')
        call = store.get('call_sessions', principal.tenant_id, id)
        conversation = call['conversation_id']
        return {'call': call, 'agents': store.list('agent_executions', principal.tenant_id, conversation),
            'tools': store.list('tool_executions', principal.tenant_id, conversation),
            'appointments': store.list('appointments', principal.tenant_id, conversation),
            'messages': store.list('messages', principal.tenant_id, conversation),
            'usage': [row for row in store.list('usage_records', principal.tenant_id) if row.get('call_id') == id]}

    @app.post('/api/calls', status_code=201)
    def start_call(config: CallCreate, principal: Principal = Depends(actor)):
        return voice.start(principal, config.assistant_id, config.locale, recording=config.recording,
                           transcript_storage=config.transcript_storage, consent_given=config.consent_given, caller=config.caller)

    @app.post('/api/calls/{id}/events')
    def call_event(id: str, config: CallEvent, principal: Principal = Depends(actor)):
        return voice.event(principal, id, config.action, locale=config.locale, text=config.text,
                           destination=config.destination, event_id=config.event_id, utterance_id=config.utterance_id,
                           final=config.final, confirmed=config.confirmed, tool=config.tool, arguments=config.arguments)

    @app.get('/api/calls/{id}/events')
    def call_history(id: str, principal: Principal = Depends(actor)):
        call = store.get('call_sessions', principal.tenant_id, id)
        return {'events': [x for x in store.list('call_events', principal.tenant_id, call['conversation_id']) if x['call_id'] == id],
                'participants': store.list('call_participants', principal.tenant_id, call['conversation_id']),
                'usage': store.list('call_usage', principal.tenant_id, call['conversation_id']),
                'executions': store.list('agent_executions', principal.tenant_id, call['conversation_id'])}

    @app.post('/api/calls/{id}/stream-ticket')
    def stream_ticket(id: str, config: Confirmation, principal: Principal = Depends(actor)):
        return {'ticket': gateway.ticket(principal, id), 'path': '/voice/media', 'expires_in_seconds': 60}

    @app.post('/api/telephony/connections', status_code=201)
    def telephony_connection(config: TelephonyConnectionCreate, principal: Principal = Depends(actor)):
        keys = ('webhook_secret', 'auth_token', 'speech_key')
        credentials = {key: getattr(config, key).get_secret_value() for key in keys}
        if config.provider == 'mock' and len(credentials['webhook_secret']) < 32 or config.provider == 'twilio' and not all(credentials[key] for key in ('auth_token', 'speech_key')):
            raise DomainError('invalid_input', 422)
        return gateway.configure(principal, config.model_dump(mode='json', exclude=set(keys)), credentials)

    @app.post('/webhooks/telephony/{tenant_id}/{connection_id}')
    async def incoming_call(tenant_id: str, connection_id: str, request: Request):
        if request.url.query:
            raise DomainError('invalid_input', 422)
        signature = request.headers.get('x-twilio-signature') or request.headers.get('x-signature', '')
        body = await request.body()
        # Provider operations and repository work are outside the HTTP event loop.
        call = await voice_runtime.threaded(gateway.incoming, tenant_id, connection_id, body, signature)
        if call['provider'] == 'twilio' and call['status'] not in ('ended', 'failed', 'transferred'):
            connection = store.get('channel_connections', tenant_id, connection_id)
            token = await voice_runtime.threaded(gateway.ticket, gateway.principal(connection), call['id'], twilio=True)
            return Response(stream_twiml(connection['public_origin'].rstrip('/'), token), media_type='application/xml')
        return call

    @app.post('/api/voice/retention')
    def voice_retention(config: Confirmation, principal: Principal = Depends(actor)):
        return {'redacted': voice.purge_expired(principal)}

    @app.get('/api/calls/{id}/transcripts')
    def transcripts(id: str, principal: Principal = Depends(actor)):
        principal.require('configure')
        call = store.get('call_sessions', principal.tenant_id, id)
        result = []
        for record in store.list('voice_transcripts', principal.tenant_id, call['conversation_id']):
            if not record.get('redacted') and datetime.fromisoformat(record['expires_at']) > voice.clock():
                result.append({**record, 'content': secrets.get(principal.tenant_id, 'transcript:' + record['id'])})
        return result

    @app.websocket('/voice/media')
    async def media_stream(websocket: WebSocket):
        import asyncio
        from types import SimpleNamespace
        transport = WebSocketAudioTransport(websocket)
        decision = limiter.check(SimpleNamespace(client=websocket.client, headers=websocket.headers,
                                                url=websocket.url, method='POST'), category_override='write')
        if not decision.allowed:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        try:
            first = await asyncio.wait_for(transport.receive(), 5)
            if first.get('event') == 'connected':
                first = await asyncio.wait_for(transport.receive(), 5)
            if first.get('event') != 'start': raise DomainError('unauthorized', 401)
            token = first.get('ticket') or first.get('start', {}).get('customParameters', {}).get('ticket')
            principal, call, is_twilio = await voice_runtime.threaded(gateway.consume_ticket, token)
            if is_twilio:
                connection = store.get('channel_connections', principal.tenant_id, call['connection_id'])
                provider, _, _ = gateway.services(connection)
                url = connection['public_origin'].rstrip('/') + '/voice/media'
                signature = websocket.headers.get('x-twilio-signature', '')
                if not provider.verify_webhook(url, b'', signature) and not provider.verify_webhook(url + '/', b'', signature):
                    raise DomainError('invalid_signature', 401)
                start = first.get('start', {})
                if start.get('callSid') != call['provider_call_id'] or start.get('accountSid') != connection['account_sid']:
                    raise DomainError('forbidden', 403)
                if start.get('mediaFormat') != {'encoding': 'audio/x-mulaw', 'sampleRate': 8000, 'channels': 1}:
                    raise DomainError('unsupported_audio', 422)
                transport.twilio, transport.stream_sid = True, first.get('streamSid')
            else:
                origin = websocket.headers.get('origin')
                if origin and origin not in ui_origins:
                    raise DomainError('forbidden', 403)
                if first.get('call_id', call['id']) != call['id']:
                    raise DomainError('forbidden', 403)
            await transport.send_event({'event': 'ready', 'call_id': call['id'], 'locale': call['voice_locale'],
                                       'state': call['state'], 'speech_validated': False})
            await voice_runtime.run(principal, call, transport)
        except (DomainError, ValidationError, ValueError, asyncio.TimeoutError):
            await websocket.close(code=1008)
        except Exception:
            await transport.close()

    @app.get('/api/settings')
    def settings(principal: Principal = Depends(actor)):
        return store.tenant(principal.tenant_id)

    @app.put('/api/settings')
    def configure(config: SettingsUpdate, principal: Principal = Depends(actor)):
        principal.require('configure')
        validate_timezone(config.timezone)
        if (config.recording_enabled or config.transcripts_enabled) and not config.notice_acknowledged:
            raise DomainError('forbidden', 403)
        changes = config.model_dump()
        tenant = {**store.tenant(principal.tenant_id), **changes}
        store.update_tenant(principal.tenant_id, tenant)
        store.audit(principal, 'tenant:configured')
        return tenant

    @app.post('/api/retention/redact')
    def redact(config: Confirmation, principal: Principal = Depends(actor)):
        principal.require('configure')
        before = (datetime.now(timezone.utc) - timedelta(days=store.tenant(principal.tenant_id)['retention_days'])).isoformat()
        count = store.purge_expired(principal.tenant_id, before)
        store.audit(principal, 'retention:redacted')
        return {'redacted_messages': count}

    @app.get('/api/connections')
    def connections(principal: Principal = Depends(actor)):
        return store.list('channel_connections', principal.tenant_id)

    @app.post('/api/connections', status_code=201)
    def connection(config: ConnectionCreate, principal: Principal = Depends(actor)):
        principal.require('configure')
        assistant = store.get('assistants', principal.tenant_id, config.assistant_id)
        if config.channel.value not in assistant['enabled_channels']:
            raise DomainError('disabled', 409)
        with store.transaction():
            data = config.model_dump(mode='json', exclude={'secret'})
            result = store.add('channel_connections', principal.tenant_id, {**data, 'state': 'MOCK', 'service_user_id': principal.user_id})
            secrets.put(principal.tenant_id, 'connection:' + result['id'], config.secret)
            store.audit(principal, 'connection:created', resource_id=result['id'])
            return result

    @app.get('/api/audit')
    def audit(principal: Principal = Depends(actor)):
        principal.require('configure')
        return store.list('audit_events', principal.tenant_id)

    @app.get('/api/templates')
    def templates(principal: Principal = Depends(actor)):
        return store.list('notification_templates', principal.tenant_id)

    @app.put('/api/templates/{id}')
    def template(id: str, config: TemplateUpdate, principal: Principal = Depends(actor)):
        from string import Formatter
        principal.require('configure')
        record = store.get('notification_templates', principal.tenant_id, id)
        try:
            fields = {field for _, field, _, _ in Formatter().parse(config.body) if field is not None}
        except ValueError:
            raise DomainError('invalid_input', 422) from None
        allowed = set(record.get('variables', ['date'] if record['key'] in ('reminder', 'appointment_created', 'appointment_rescheduled') else []))
        if fields != allowed or any(spec or conversion for _, _, spec, conversion in Formatter().parse(config.body)):
            raise DomainError('invalid_input', 422)
        store.audit(principal, 'template:configured', resource_id=id)
        return store.update('notification_templates', principal.tenant_id, id, config.model_dump())

    @app.get('/api/jobs')
    def job_history(principal: Principal = Depends(actor)):
        return store.list('jobs', principal.tenant_id)

    @app.post('/api/jobs/run')
    def run_jobs(config: Confirmation, principal: Principal = Depends(actor)):
        return jobs.run_due(principal, at=orchestrator.clock()) + messaging.run(principal)

    @app.post('/webhooks/mock/{tenant_id}/{connection_id}')
    async def webhook(tenant_id: str, connection_id: str, request: Request):
        connection = store.get('channel_connections', tenant_id, connection_id)
        raw = await request.body()
        adapter = providers.channels[connection['channel']]
        if not adapter.verify_signature(raw, request.headers.get('x-signature', ''), secrets.get(tenant_id, 'connection:' + connection_id)):
            raise DomainError('invalid_signature', 401)
        try:
            payload = json.loads(raw)
            normalized = adapter.normalize(payload)
        except (ValueError, ValidationError, TypeError):
            raise DomainError('invalid_input', 422) from None
        if normalized.tenant_id != tenant_id or normalized.assistant_id != connection['assistant_id']:
            raise DomainError('forbidden', 403)
        conversation = store.get('conversations', tenant_id, normalized.conversation_id)
        if conversation['assistant_id'] != connection['assistant_id'] or conversation['channel'] != connection['channel']:
            raise DomainError('forbidden', 403)
        if conversation.get('contact_id'):
            contact = store.get('contacts', tenant_id, conversation['contact_id'])
            if normalized.sender != contact['address']:
                raise DomainError('forbidden', 403)
        user = store.get('users', tenant_id, connection['service_user_id'])
        if not user.get('enabled', True):
            raise DomainError('forbidden', 403)
        principal = Principal(tenant_id, user['id'], user['role'], user['subject'])
        return orchestrator.inbound(principal, normalized.conversation_id,
            Incoming(content=normalized.content, event_id=connection_id + ':' + normalized.external_id, locale=normalized.locale),
            sender=normalized.sender, recipient=normalized.recipient, attachments=normalized.attachments)

    @app.post('/webhooks/mock/{tenant_id}/{connection_id}/status')
    async def callback(tenant_id: str, connection_id: str, request: Request):
        connection = store.get('channel_connections', tenant_id, connection_id)
        raw = await request.body()
        adapter = providers.channels[connection['channel']]
        if not adapter.verify_signature(raw, request.headers.get('x-signature', ''), secrets.get(tenant_id, 'connection:' + connection_id)):
            raise DomainError('invalid_signature', 401)
        try:
            payload = StatusCallback.model_validate_json(raw)
        except ValidationError:
            raise DomainError('invalid_input', 422) from None
        with store.transaction():
            key = event_key('status:' + connection_id, payload.event_id)
            existing = store.find('provider_events', tenant_id, key)
            if existing:
                return {**existing['result'], 'duplicate': True}
            id = payload.external_id.removeprefix('mock:')
            message = store.get('messages', tenant_id, id)
            if message['assistant_id'] != connection['assistant_id'] or message['channel'] != connection['channel'] or message.get('direction') != 'outbound':
                raise DomainError('forbidden', 403)
            result = adapter.status_callback(payload.model_dump())
            current = message.get('delivery', {}).get('status', 'simulated')
            transitions = {'simulated': {'sent', 'delivered', 'read', 'failed'}, 'sent': {'delivered', 'read', 'failed'}, 'delivered': {'read'}, 'read': set(), 'failed': set()}
            if result['status'] != current and result['status'] not in transitions.get(current, set()):
                raise DomainError('invalid_transition', 409)
            store.update('messages', tenant_id, id, {'status': result['status'], 'delivery': {**message.get('delivery', {}), **result}})
            store.add('provider_events', tenant_id, {'result': result, 'timestamp': now()}, external_key=key)
            return result

    register_messaging(app, messaging, actor)
    register_saas(app, billing, identity, actor, platform_subjects, privacy, backups)
    from .connectors import ConnectorService, register_connectors
    app.state.connectors=ConnectorService(store,secrets,enabled=connector_fixtures and demo_enabled and not strict,clock=orchestrator.clock)
    register_connectors(app,app.state.connectors,actor)
    from .customer_oauth import CustomerOAuthService, register_customer_oauth
    app.state.customer_oauth=CustomerOAuthService(store,secrets,clock=orchestrator.clock,**(customer_oauth_options or {}))
    register_customer_oauth(app,app.state.customer_oauth,actor)
    from .customer_workspace import register_customer_workspace
    register_customer_workspace(app,store,actor,billing,clock)
    return app
