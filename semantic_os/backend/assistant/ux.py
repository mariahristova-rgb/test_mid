"""Tenant-owned setup drafts and strictly offline regression runs.

Uses existing operations-event persistence. No live provider, calendar, or messaging
object is passed to a simulation. Fixed synthetic inputs never copy patient text.
"""
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import json
from threading import BoundedSemaphore
from time import monotonic
from typing import Literal
from zoneinfo import ZoneInfo
from fastapi import Depends
from pydantic import Field, field_validator, model_validator
from .domain import AssistantConfig, Contract, DomainError, Incoming, Locale, Principal
from .orchestration import Orchestrator
from .providers import ProviderRegistry
from .store import Store, now, uid
from .voice import TERMINAL

SCENARIOS = ('booking', 'short_confirmation', 'rejection', 'ambiguous', 'occupied', 'language_switch', 'handoff', 'interruption','faq','greeting')


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


class Business(Contract):
    name: str = Field(min_length=1, max_length=120)
    website: str = Field(default='',max_length=500)
    industry: str = Field(default='',max_length=120)
    timezone: str = 'Europe/Sofia'
    weekdays: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4], min_length=1, max_length=7)
    opens: str = '09:00'
    closes: str = '18:00'
    service: str = Field(default='Consultation', min_length=1, max_length=120)
    duration_minutes: int = Field(default=30, ge=5, le=480)

    @field_validator('timezone')
    @classmethod
    def zone(cls, value):
        try: ZoneInfo(value)
        except Exception: raise ValueError('invalid timezone') from None
        return value

    @model_validator(mode='after')
    def hours(self):
        import re
        if any(type(day) is not int or day not in range(7) for day in self.weekdays) or len(set(self.weekdays)) != len(self.weekdays):
            raise ValueError('invalid weekdays')
        for value in (self.opens, self.closes):
            if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value): raise ValueError('invalid hours')
        if self.opens >= self.closes: raise ValueError('invalid hours')
        return self


class DraftInput(Contract):
    revision: int = Field(default=0, ge=0)
    assistant_id: str | None = None
    use_case: Literal['receptionist', 'support', 'general','sales'] = 'receptionist'
    step: int = Field(default=0, ge=0, le=6)
    config: AssistantConfig
    business: Business


class RunInput(Contract):
    revision: int = Field(ge=1)
    scenario: Literal['booking', 'short_confirmation', 'rejection', 'ambiguous', 'occupied', 'language_switch', 'handoff', 'interruption','faq','greeting']
    locale: Locale


class ConfirmInput(Contract):
    revision: int = Field(ge=1)
    confirmed: bool = False


class UXService:
    def __init__(self, store, providers, valid_config):
        self.store, self.providers, self.valid_config = store, providers, valid_config
        self.slots = BoundedSemaphore(1)

    def rows(self, tenant, kind):
        return [row for row in self.store.list('operations_events', tenant) if row.get('kind') == kind]

    def draft(self, principal, identity):
        row = self.store.get('operations_events', principal.tenant_id, identity)
        if row.get('kind') != 'ux_draft': raise DomainError('not_found', 404)
        return row

    def save(self, principal, payload, identity=None):
        principal.require('configure')
        config = payload.config.model_dump(mode='json')
        # Config is validated by its normal contracts, never used to call a provider.
        if set(config['assigned_agents']) != {'receptionist', 'executor'}: raise DomainError('invalid_input', 422)
        from .tools import SCHEMAS
        if not set(config['allowed_tools']) <= set(SCHEMAS): raise DomainError('invalid_input', 422)
        if config['booking_duration_minutes'] != payload.business.duration_minutes: raise DomainError('invalid_input', 422)
        with self.store.transaction():
            previous = self.draft(principal, identity) if identity else None
            if previous and (previous['revision'] != payload.revision or previous['status'] != 'draft'):
                raise DomainError('conflict', 409)
            if not previous and payload.revision: raise DomainError('conflict', 409)
            if not previous and len(self.rows(principal.tenant_id, 'ux_draft')) >= 50: raise DomainError('limit_reached', 429)
            assistant = self.store.get('assistants', principal.tenant_id, payload.assistant_id) if payload.assistant_id else None
            if previous and previous.get('target_assistant_id') != payload.assistant_id: raise DomainError('conflict', 409)
            data = {'kind': 'ux_draft', 'status': 'draft', 'revision': payload.revision + 1,
                'target_assistant_id': payload.assistant_id, 'base_hash': previous['base_hash'] if previous else digest(assistant),
                'config': config, 'business': payload.business.model_dump(), 'step': payload.step,
                'use_case': payload.use_case, 'timestamp': now()}
            # Agent permission changes invalidate receipts without overwriting shared agents.
            data['agents'] = [{k: row[k] for k in ('id', 'enabled', 'instructions', 'allowed_tools', 'supported_locales')}
                for row in self.store.list('agents', principal.tenant_id)]
            tenant = self.store.tenant(principal.tenant_id)
            data['calendar_base'] = tenant.get('calendar_policy', {})
            data['tenant_base_hash'] = digest({key:tenant.get(key) for key in ('name','timezone','calendar_policy')})
            data['config_hash'] = digest({key: data[key] for key in ('config', 'business', 'agents', 'use_case','calendar_base')})
            result = self.store.update('operations_events', principal.tenant_id, identity, data) if previous else self.store.add('operations_events', principal.tenant_id, data)
            self.store.audit(principal, 'setup:saved', resource_id=result['id'])
            return result

    def test(self, principal, identity, payload):
        principal.require('execute')
        draft = self.draft(principal, identity)
        if draft['status'] != 'draft' or draft['revision'] != payload.revision: raise DomainError('conflict', 409)
        if not self.slots.acquire(blocking=False): raise DomainError('test_worker_busy', 429)
        start = monotonic()
        try:
            if len(self.rows(principal.tenant_id, 'ux_test')) >= 500: raise DomainError('limit_reached', 429)
            receipt = self.simulate(draft, payload)
            receipt.update(kind='ux_test', draft_id=identity, revision=draft['revision'], config_hash=draft['config_hash'],
                scenario=payload.scenario, locale=payload.locale, duration_ms=round((monotonic()-start)*1000, 3), timestamp=now(),
                scope='isolated_text_mock', voice_verified=False)
            result = self.store.add('operations_events', principal.tenant_id, receipt)
            self.store.audit(principal, 'setup:test', resource_id=result['id'], status=receipt['verdict'])
            return result
        finally: self.slots.release()

    def simulate(self, draft, payload):
        if payload.scenario == 'interruption':
            return {'verdict': 'BLOCKED', 'code': 'audio_test_unavailable', 'turns': [], 'tools': [], 'agents': [], 'booking_count': 0}
        sandbox = Store()
        try:
            sandbox.seed()
            business = draft['business']
            tenant = sandbox.tenant('demo')
            tenant.update(name=business['name'], timezone=business['timezone'], calendar_policy={
                'weekdays': business['weekdays'], 'opens': business['opens'], 'closes': business['closes'],
                'slot_minutes': draft['calendar_base'].get('slot_minutes', 1), 'duration_minutes': business['duration_minutes'],
                'resources': draft['calendar_base'].get('resources', [{'id': 'synthetic-resource'}]), 'service_id': business['service']})
            sandbox.update_tenant('demo', tenant)
            config = {**draft['config'], 'llm_provider': 'mock', 'voice_provider': 'mock', 'status': 'active', 'enabled_channels': ['web_chat']}
            sandbox.update('assistants', 'demo', 'default', config)
            for agent in draft['agents']:
                sandbox.update('agents', 'demo', agent['id'], {k:v for k,v in agent.items() if k != 'id'})
            clock = datetime(2030, 10, 8, 9, tzinfo=timezone.utc)
            engine = Orchestrator(sandbox, ProviderRegistry(), clock=lambda: clock)
            from .messaging import MessagingGateway
            from .security import TenantSecretStore
            MessagingGateway(sandbox, TenantSecretStore(sandbox), engine)
            actor = sandbox.principal('demo-admin', 'demo')
            conversation = engine.conversation(actor, 'default')
            bg = payload.locale == 'bg-BG'
            inputs = [('Здравейте, искам да запиша час за утре в 15:00.' if bg else 'Hello, I would like to book an appointment for tomorrow at 15:00.'),
                ('Казвам се Иван Иванов.' if bg else 'My name is John Smith.'), ('Да, потвърждавам.' if bg else 'Yes, confirm.')]
            if payload.scenario == 'short_confirmation': inputs[-1] = 'Да.' if bg else 'Yes.'
            if payload.scenario == 'rejection': inputs[-1] = 'Не.' if bg else 'No.'
            if payload.scenario == 'ambiguous': inputs[-1] = 'Да, потвърждавам?' if bg else 'Yes, confirm?'
            if payload.scenario == 'language_switch': inputs.insert(2, 'Switch to English.' if bg else 'Премини на български.'); inputs[-1] = 'Yes, confirm.' if bg else 'Да, потвърждавам.'
            if payload.scenario == 'handoff': inputs = ['Искам да говоря с човек.' if bg else 'I want to speak to a human.']
            if payload.scenario=='greeting':inputs=['Здравейте.' if bg else 'Hello.']
            if payload.scenario=='faq':
                if not config['faq_entries']:return {'verdict':'BLOCKED','code':'faq_missing','turns':[],'tools':[],'agents':[],'booking_count':0}
                inputs=[config['faq_entries'][0]['question_bg' if bg else 'question_en']]
            if payload.scenario == 'occupied':
                zone=ZoneInfo(business['timezone'])
                day=clock.astimezone(zone).date()+timedelta(days=1)
                starts = datetime(day.year,day.month,day.day,15,tzinfo=zone).isoformat()
                sandbox.add('appointments', 'demo', {'starts_at': starts, 'duration_minutes': business['duration_minutes'], 'status': 'confirmed', 'synthetic': True})
                inputs = inputs[:1]
            turns, code = [], 'completed'
            for text in inputs:
                turn_start = monotonic()
                try:
                    result = engine.inbound(actor, conversation['id'], Incoming(content=text, event_id=uid(),locale=payload.locale if payload.scenario in ('faq','greeting') else None))
                    turns.append({'input': text, 'response': result['response'], 'locale': result['locale'],
                        'booking_status': result.get('booking_status'), 'duration_ms': round((monotonic()-turn_start)*1000, 3)})
                except DomainError as error:
                    code = error.code
                    break
            bookings = [row for row in sandbox.list('appointments', 'demo') if not row.get('synthetic')]
            state = sandbox.get('conversations', 'demo', conversation['id'])
            wanted = 0 if payload.scenario in ('rejection', 'ambiguous', 'occupied', 'handoff','faq','greeting') else 1
            last = turns[-1] if turns else {}
            checks = {'booking_count': len(bookings) == wanted, 'no_error': code == 'completed'}
            if payload.scenario == 'ambiguous': checks['confirmation_pending'] = last.get('booking_status') == 'awaiting_confirmation'
            if payload.scenario == 'rejection': checks['rejected'] = last.get('booking_status') == 'cancelled'
            if payload.scenario == 'occupied': checks['unavailable'] = last.get('booking_status') == 'unavailable'
            if payload.scenario == 'handoff': checks['paused'] = bool(state.get('human_escalation'))
            if payload.scenario=='faq':checks['faq_answer']=last.get('response')==config['faq_entries'][0]['answer_bg' if bg else 'answer_en']
            if payload.scenario == 'language_switch': checks['switched'] = last.get('locale') == ('en-US' if bg else 'bg-BG')
            return {'verdict': 'PASS' if all(checks.values()) else 'FAIL', 'code': code, 'checks': checks, 'turns': turns,
                'booking_count': len(bookings), 'expected_booking_count': wanted,
                'reference_at': clock.isoformat(), 'timezone': business['timezone'],
                'tools': [{'tool': row['tool'], 'code': row['outcome']['code'], 'correlation_id': row['correlation_id']} for row in sandbox.list('tool_executions', 'demo')],
                'agents': [{'source': row['handoff']['source_agent'], 'target': row['handoff']['target_agent'], 'locale': row['handoff']['locale']} for row in sandbox.list('agent_executions', 'demo') if row.get('handoff')]}
        finally: sandbox.close()

    def readiness(self, principal, draft):
        current_agents = [{k: row[k] for k in ('id', 'enabled', 'instructions', 'allowed_tools', 'supported_locales')} for row in self.store.list('agents', principal.tenant_id)]
        receipts = [row for row in self.rows(principal.tenant_id, 'ux_test') if row['draft_id'] == draft['id'] and row['config_hash'] == draft['config_hash']]
        cutoff = datetime.now(timezone.utc)-timedelta(days=7)
        def fresh(row):
            try:return cutoff<=datetime.fromisoformat(row['timestamp'])<=datetime.now(timezone.utc)+timedelta(seconds=30)
            except (KeyError,ValueError,TypeError):return False
        latest = {(row['scenario'],row['locale']): row for row in receipts if fresh(row)}
        scenarios=['booking','rejection','ambiguous'] if {'CheckAvailability','CreateAppointment'}<=set(draft['config']['allowed_tools']) else ['greeting']
        if draft['config']['faq_entries']:scenarios.append('faq')
        required = [(scenario, locale) for scenario in scenarios for locale in ('bg-BG','en-US')]
        tests = all(latest.get(key, {}).get('verdict') == 'PASS' for key in required)
        targets = draft['config']['enabled_channels']
        reasons = []
        if draft['status'] != 'draft': reasons.append('draft_closed')
        if draft['config']['status'] != 'active': reasons.append('assistant_disabled')
        if current_agents != draft['agents']: reasons.append('agent_config_changed')
        tenant = self.store.tenant(principal.tenant_id)
        if digest({key:tenant.get(key) for key in ('name','timezone','calendar_policy')}) != draft['tenant_base_hash']: reasons.append('business_config_changed')
        if not tests: reasons.append('required_tests_missing')
        if not {'bg-BG','en-US'}<=set(draft['config']['supported_locales']):reasons.append('language_coverage_missing')
        if receipts and not any(fresh(row) for row in receipts):reasons.append('test_evidence_expired')
        if targets != ['web_chat']: reasons.append('external_activation_blocked')
        if 'voice' in targets: reasons.append('voice_acceptance_blocked')
        if draft['config']['llm_provider'] != 'mock': reasons.append('mock_test_not_live_proof')
        if 'SendMessage' in draft['config']['allowed_tools']: reasons.append('outbound_tool_blocked')
        if any(row['status'] not in TERMINAL for row in self.store.list('call_sessions',principal.tenant_id)): reasons.append('active_calls_block_activation')
        if any(row.get('status')=='pending' for row in self.store.list('approvals',principal.tenant_id)): reasons.append('pending_approvals_block_activation')
        connections = self.store.list('channel_connections', principal.tenant_id)
        def channel_status(channel):
            if channel == 'web_chat': return 'MOCK_ONLY' if draft['config']['llm_provider'] == 'mock' else 'CONFIGURED'
            if channel == 'voice':
                voice = draft['config']['voice_settings']
                if voice['telephony_provider'] == 'mock': return 'MOCK_ONLY'
                return 'CONFIGURED' if voice['telephony_provider'] == 'asterisk' and self.providers.asterisk else 'NOT_CONFIGURED'
            rows = [row for row in connections if row.get('channel') == channel and row.get('enabled')]
            if any(row.get('last_error') for row in rows): return 'ERROR'
            if not rows: return 'NOT_CONFIGURED'
            return 'MOCK_ONLY' if all(row.get('provider') == 'mock' for row in rows) else 'CONFIGURED'
        return {'can_publish': not reasons, 'reasons': reasons, 'scope': 'web_chat_mock_calendar', 'voice_live_verified': False,'evidence_max_age_days':7,
            'required_tests': [{'scenario': key[0], 'locale': key[1], 'verdict': latest.get(key, {}).get('verdict', 'NOT_RUN')} for key in required],
            'channels': [{'channel': channel, 'status': channel_status(channel)} for channel in targets]}

    def publish(self, principal, identity, payload):
        principal.require('configure')
        if not payload.confirmed: raise DomainError('forbidden', 403)
        with self.store.transaction():
            draft = self.draft(principal, identity)
            if draft['revision'] != payload.revision: raise DomainError('conflict', 409)
            if not self.readiness(principal, draft)['can_publish']: raise DomainError('conflict', 409)
            if any(row['status'] not in TERMINAL for row in self.store.list('call_sessions', principal.tenant_id)):
                raise DomainError('conflict', 409)
            if any(row.get('status') == 'pending' for row in self.store.list('approvals', principal.tenant_id)):
                raise DomainError('conflict', 409)
            target = draft.get('target_assistant_id')
            current = self.store.get('assistants', principal.tenant_id, target) if target else None
            if digest(current) != draft['base_hash']: raise DomainError('conflict', 409)
            self.valid_config(AssistantConfig.model_validate(draft['config']))
            result = self.store.update('assistants', principal.tenant_id, target, draft['config']) if target else self.store.add('assistants', principal.tenant_id, draft['config'])
            self.store.add('operations_events', principal.tenant_id, {'kind': 'ux_version', 'target_assistant_id': result['id'],
                'config': draft['config'], 'previous_config': current, 'config_hash': draft['config_hash'],
                'revision':draft['revision'], 'draft_id':draft['id'], 'timestamp': now()})
            business = draft['business']
            tenant = self.store.tenant(principal.tenant_id)
            old_policy = tenant.get('calendar_policy', {})
            tenant.update(name=business['name'],website=business.get('website',''),industry=business.get('industry',''),timezone=business['timezone'], calendar_policy={**old_policy,
                'weekdays': business['weekdays'], 'opens': business['opens'], 'closes': business['closes'],
                'duration_minutes': business['duration_minutes'], 'slot_minutes': old_policy.get('slot_minutes', 1),
                'resources': old_policy.get('resources', [{'id': 'mock-resource'}]), 'service_id': business['service']})
            self.store.update_tenant(principal.tenant_id, tenant)
            self.store.update('operations_events', principal.tenant_id, identity, {'status': 'published', 'published_assistant_id': result['id'],
                'published_business_hash':digest({key:tenant.get(key) for key in ('timezone','calendar_policy')})})
            self.store.audit(principal, 'setup:published', resource_id=result['id'])
            return result


def register_ux(app, store, providers, actor, valid_config):
    service = UXService(store, providers, valid_config)
    app.state.ux = service

    @app.get('/api/ux/assistants/{identity}/summary')
    def assistant_summary(identity: str, principal: Principal = Depends(actor)):
        store.get('assistants',principal.tenant_id,identity)
        counts={table:sum(row.get('assistant_id')==identity for row in store.list(table,principal.tenant_id)) for table in ('conversations','call_sessions')}
        versions=[{key:row.get(key) for key in ('id','timestamp','config_hash','revision')} for row in service.rows(principal.tenant_id,'ux_version') if row.get('target_assistant_id')==identity]
        return {'counts':counts,'versions':versions,'scope':'all_stored_records','rollback_supported':False}

    @app.get('/api/ux/conversations/{identity}/diagnostics')
    def diagnostics(identity: str, principal: Principal = Depends(actor)):
        principal.require('approve')
        conversation = store.get('conversations', principal.tenant_id, identity)
        calls = [row for row in store.list('call_sessions', principal.tenant_id, identity)]
        timeline = []
        def event(kind, row, **details):
            timeline.append({'kind': kind, 'id': row['id'], 'timestamp': row.get('timestamp') or row.get('at'),
                'correlation_id': row.get('correlation_id'), **details})
        for row in store.list('call_events', principal.tenant_id, identity):
            event('channel_event', row, code=row.get('event') or row.get('action'), status=row.get('status'))
        for row in store.list('agent_executions', principal.tenant_id, identity):
            handoff = row.get('handoff', {})
            event('agent_handoff', row, source=handoff.get('source_agent'), target=handoff.get('target_agent'),
                locale=handoff.get('locale'), status=row.get('status'))
        for row in store.list('tool_executions', principal.tenant_id, identity):
            event('tool_result', row, tool=row.get('tool'), code=row.get('outcome',{}).get('code'),
                status=row.get('outcome',{}).get('status'))
        timeline.sort(key=lambda row: (row['timestamp'] is None, row['timestamp'] or '', row['id']))
        bookings = [{key: row.get(key) for key in ('id', 'status', 'starts_at', 'timezone', 'duration_minutes')}
            for row in store.list('appointments', principal.tenant_id, identity)]
        traces = [row for row in store.operations.snapshot(principal.tenant_id)['voice_trace'] if row.get('conversation_id') == identity] if conversation['channel'] == 'voice' else []
        # Monotonic trace timestamps belong to one process, not wall-clock dates.
        messages = []
        for row in store.list('messages', principal.tenant_id, identity):
            messages.append({key: row.get(key) for key in ('id','direction','locale','timestamp','delivery_status')})
        state = conversation.get('booking_state') or {}
        stages = []
        for key, recorded in [('agent_handoff',any(row['kind']=='agent_handoff' for row in timeline)),
            ('availability',any(row.get('tool') in ('CheckAvailability','ConciergeAvailability') for row in timeline)),
            ('confirmation_pending',bool(state.get('approval_id'))), ('booking_persisted',bool(bookings))]:
            stages.append({'stage':key,'coverage':'recorded' if recorded else 'not_recorded'})
        for key in ('audio_received','vad_final','stt_final','locale_selected','tts_completed','output_packet_sent','session_closed'):
            stages.append({'stage':key,'coverage':'not_applicable' if conversation['channel'] != 'voice' else 'recorded' if any(row['stage']==key for row in traces) else 'not_recorded'})
        return {'conversation_id': identity, 'channel': conversation['channel'], 'locale': conversation.get('active_locale'),
            'human_escalation': bool(conversation.get('human_escalation')), 'status': conversation['status'],
            'booking_status': state.get('status') or (bookings[-1]['status'] if bookings else None), 'appointments': bookings,
            'calls': [{key: row.get(key) for key in ('id','status','started_at','ended_at','error_code')} for row in calls],
            'timeline': timeline, 'voice_trace': traces, 'message_metadata': messages, 'stage_coverage':stages,
            'transcripts': 'not_exposed', 'trace_scope': 'bounded_process_memory',
            'voice_coverage': 'recorded' if traces else 'not_recorded' if conversation['channel'] == 'voice' else 'not_applicable',
            'suggested_scenario': 'ambiguous' if not bookings else 'booking'}

    @app.get('/api/ux/drafts')
    def drafts(principal: Principal = Depends(actor)):
        principal.require('execute')
        return service.rows(principal.tenant_id, 'ux_draft')

    @app.post('/api/ux/drafts', status_code=201)
    def create(payload: DraftInput, principal: Principal = Depends(actor)):
        return service.save(principal, payload)

    @app.put('/api/ux/drafts/{identity}')
    def save(identity: str, payload: DraftInput, principal: Principal = Depends(actor)):
        return service.save(principal, payload, identity)

    @app.get('/api/ux/drafts/{identity}/readiness')
    def readiness(identity: str, principal: Principal = Depends(actor)):
        principal.require('execute')
        return service.readiness(principal, service.draft(principal, identity))

    @app.post('/api/ux/drafts/{identity}/tests')
    def run(identity: str, payload: RunInput, principal: Principal = Depends(actor)):
        return service.test(principal, identity, payload)

    @app.get('/api/ux/drafts/{identity}/tests')
    def results(identity: str, principal: Principal = Depends(actor)):
        principal.require('execute'); service.draft(principal, identity)
        return [row for row in service.rows(principal.tenant_id, 'ux_test') if row['draft_id'] == identity]

    @app.post('/api/ux/drafts/{identity}/publish')
    def publish(identity: str, payload: ConfirmInput, principal: Principal = Depends(actor)):
        return service.publish(principal, identity, payload)

    @app.post('/api/ux/drafts/{identity}/cancel')
    def cancel(identity: str, payload: ConfirmInput, principal: Principal = Depends(actor)):
        principal.require('configure')
        if not payload.confirmed: raise DomainError('forbidden', 403)
        with store.transaction():
            draft = service.draft(principal, identity)
            if draft['revision'] != payload.revision or draft['status'] != 'draft': raise DomainError('conflict', 409)
            result = store.update('operations_events', principal.tenant_id, identity, {'status': 'cancelled'})
            store.audit(principal, 'setup:cancelled', resource_id=identity)
            return result
