"""Dedicated fictional fixture only; reset archives actions and preserves the audit/usage ledger."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from .domain import DomainError, AssistantConfig
from .calendar import MockCalendarProvider
from .store import now

TENANT, MARKER = 'smilecare-demo', 'testmid-smilecare-synthetic-v1'


def seed_smilecare(store, *, mode='qwen', clock=None, operator_subject='demo-admin', tts='piper'):
    if mode not in ('qwen', 'mock'): raise DomainError('invalid_input', 422)
    clock = clock or (lambda: datetime.now(timezone.utc))
    with store.transaction():
        try:
            tenant = store.tenant(TENANT)
            if tenant.get('demo_marker') != MARKER: raise DomainError('forbidden', 403)
            return {'tenant_id': TENANT, 'assistant_id': 'default', 'created': False, 'llm_provider': store.get('assistants', TENANT, 'default')['llm_provider']}
        except DomainError as exc:
            if exc.code != 'not_found': raise
        store.seed(TENANT, 'smilecare-demo-admin')
        if operator_subject != 'smilecare-demo-admin':
            store.add('users', TENANT, {'subject':operator_subject, 'role':'admin', 'enabled':True, 'preferred_locale':'bg-BG'}, external_key=operator_subject)
        tenant = store.tenant(TENANT)
        dentists = [{'id': 'fictional-dentist-a', 'name_bg': 'Д-р Елена Демо', 'name_en': 'Dr Elena Demo'},
            {'id': 'fictional-dentist-b', 'name_bg': 'Д-р Никола Пример', 'name_en': 'Dr Nikola Example'}]
        store.update_tenant(TENANT, {**tenant, 'name':'SmileCare Demo Clinic', 'demo_marker': MARKER,
            'calendar_policy': {'weekdays': [0,1,2,3,4], 'opens':'09:00', 'closes':'18:00', 'slot_minutes':30,
                'duration_minutes':30, 'resources':dentists, 'service_id':'dental-checkup'},
            'services':[{'id':'dental-checkup', 'name_bg':'Профилактичен преглед', 'name_en':'Dental checkup', 'duration_minutes':30}]})
        config = AssistantConfig(name='SmileCare Receptionist', llm_provider=mode, booking_duration_minutes=30,
            llm_settings={'model':'Qwen3-4B', 'max_tokens':256, 'temperature':.2} if mode == 'qwen' else {'max_tokens':256, 'temperature':.2},
            enabled_channels=['voice','web_chat'], instructions='Fictional SmileCare clinic. Dental checkup: 30 minutes, Monday–Friday 09:00–18:00 Europe/Sofia. Use only verified tool results.').model_dump(mode='json')
        config['voice_settings']['greetings'] = {'bg-BG':'Здравейте! Свързахте се със SmileCare. Как мога да Ви помогна?',
            'en-US':'Hello! You have reached SmileCare. How can I help you?'}
        if mode == 'qwen':
            config['voice_settings'].update(telephony_provider='asterisk', stt_provider='faster_whisper', tts_provider='piper',
                voices={'bg-BG':'approved-bg', 'en-US':'approved-en'})
            if tts=='espeak_ng': config['voice_settings'].update(tts_provider='espeak_ng',
                voices={'bg-BG':'espeak-bg','en-US':'espeak-en'})
            config['voice_settings']['max_concurrent_calls']=1
            config['voice_settings']['max_latency_ms']=90000
        store.update('assistants', TENANT, 'default', config)
        for name, address, locale in (('Мария Демо','maria@example.invalid','bg-BG'),('Jane Example','jane@example.invalid','en-US')):
            store.add('contacts', TENANT, {'name':name, 'address':address, 'preferred_locale':locale, 'synthetic':True}, external_key=address)
        conversation = store.add('conversations', TENANT, {'assistant_id':'default', 'channel':'web_chat', 'active_locale':'bg-BG',
            'status':'closed', 'synthetic':True, 'human_escalation':False}, external_key='seed-samples')
        reference = clock().astimezone(ZoneInfo('Europe/Sofia'))
        day = reference.date()+timedelta(days=(0-reference.weekday())%7 or 7)
        starts = datetime.combine(day, datetime.min.time(), reference.tzinfo).replace(hour=14)
        calendar = MockCalendarProvider(store)
        for name in ('Synthetic Sample A','Synthetic Sample B'):
            appointment = calendar.create(TENANT, {'starts_at': starts.isoformat(), 'duration_minutes':30, 'contact_name':name}, conversation, 'Europe/Sofia')
            store.update('appointments', TENANT, appointment['id'], {'synthetic':True, 'seeded_fixture':True})
        return {'tenant_id':TENANT, 'assistant_id':'default', 'created':True, 'llm_provider':mode}


def reset_smilecare(store, principal):
    principal.require('configure')
    if principal.tenant_id != TENANT or store.tenant(TENANT).get('demo_marker') != MARKER: raise DomainError('forbidden', 403)
    with store.transaction():
        if any(call['status'] not in ('ended','failed','transferred') for call in store.list('call_sessions', TENANT)):
            raise DomainError('conflict', 409)
        for table, states in (('appointments', {'confirmed'}), ('approvals', {'pending'}), ('jobs', {'pending','retry'})):
            for row in store.list(table, TENANT):
                if table == 'appointments' and row.get('seeded_fixture') is True:
                    continue  # Required fictional unavailable-slot fixtures survive reset.
                if row.get('status') in states: store.update(table, TENANT, row['id'], {'status':'cancelled'})
        for row in store.list('conversations', TENANT): store.update('conversations', TENANT, row['id'], {'status':'closed'})
        store.audit(principal, 'demo:reset', status='archived')
        return {'tenant_id':TENANT, 'status':'archived', 'timestamp':now()}
