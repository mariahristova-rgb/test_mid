"""Offline setup/simulation boundaries, including live-store side effects."""
import unittest
from semantic_os.backend.assistant.domain import AssistantConfig, DomainError, Channel
from semantic_os.backend.assistant.providers import ProviderRegistry
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.ux import UXService, DraftInput, RunInput, ConfirmInput


class UXTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(); self.store.seed(); self.store.seed('other', 'other')
        self.actor = self.store.principal('demo-admin', 'demo')
        self.ux = UXService(self.store, ProviderRegistry(), lambda config: None)
        self.payload = DraftInput(config=AssistantConfig(name='Synthetic clinic', enabled_channels=['web_chat'],allowed_tools=['CheckAvailability','CreateAppointment','EscalateToHuman']), business={'name': 'Synthetic clinic'})

    def tearDown(self): self.store.close()

    def run_case(self, draft, scenario, locale='bg-BG'):
        return self.ux.test(self.actor, draft['id'], RunInput(revision=draft['revision'], scenario=scenario, locale=locale))

    def test_optional_business_defaults_and_invalid_fields(self):
        from pydantic import ValidationError
        from semantic_os.backend.assistant.ux import Business
        legacy=Business(name='Legacy business')
        self.assertEqual(legacy.holidays,[]);self.assertEqual(legacy.service_price,'')
        self.assertEqual(Business(name='Synthetic',service_price='12,50').service_price,'12.50')
        for change in ({'service_price':'-1'},{'service_price':'1.234'},{'contact_email':'bad\nheader'},
                       {'holidays':['2030-02-31']},{'holidays':['2030-10-10']*2},
                       {'unavailable_periods':[{'starts_at':'2030-10-10T12:00:00','ends_at':'2030-10-10T13:00:00'}]},
                       {'unavailable_periods':[{'starts_at':'2030-10-10T13:00:00Z','ends_at':'2030-10-10T12:00:00Z'}]}):
            with self.subTest(change=change):
                with self.assertRaises(ValidationError):Business(name='Synthetic',**change)

    def test_business_setup_resume_publish_and_mock_schedule_isolation(self):
        from semantic_os.backend.assistant.ux import Business
        from semantic_os.backend.assistant.calendar import MockCalendarProvider
        before=self.store.tenant('demo');other=self.store.tenant('other')
        self.payload.business=Business(name='Synthetic clinic',description='Synthetic public service',contact_email='owner@example.invalid',
            contact_phone='Synthetic phone',service_price='123.45',price_currency='EUR',holidays=['2030-10-10'],
            unavailable_periods=[{'starts_at':'2030-10-11T12:00:00Z','ends_at':'2030-10-11T13:00:00Z'}])
        draft=self.ux.save(self.actor,self.payload)
        saved=self.ux.draft(self.actor,draft['id'])
        self.assertEqual(saved['business']['service_price'],'123.45')
        self.assertIsInstance(saved['business']['unavailable_periods'][0]['starts_at'],str)
        self.assertEqual(self.store.tenant('demo'),before)
        for locale in ('bg-BG','en-US'):
            for scenario in ('booking','rejection','ambiguous'):self.assertEqual(self.run_case(draft,scenario,locale)['verdict'],'PASS')
        configured=self.ux.publish(self.actor,draft['id'],ConfirmInput(revision=1,confirmed=True))
        self.assertEqual(configured['enabled_channels'],['web_chat']);self.assertEqual(configured['llm_provider'],'mock')
        tenant=self.store.tenant('demo');self.assertEqual(tenant['contact_email'],'owner@example.invalid')
        self.assertEqual(tenant['description'],'Synthetic public service')
        calendar=MockCalendarProvider(self.store)
        self.assertFalse(calendar.available('demo','2030-10-10T12:00:00+03:00',30))
        self.assertFalse(calendar.available('demo','2030-10-11T12:15:00Z',30))
        self.assertTrue(calendar.available('demo','2030-10-11T13:00:00Z',30))
        self.assertTrue(calendar.available('other','2030-10-10T12:00:00+03:00',30))
        self.assertEqual(self.store.tenant('other'),other);self.assertEqual(self.store.count('appointments','demo'),0)

    def test_closed_dates_are_enforced_inside_disposable_simulation(self):
        self.payload.business.holidays=['2030-10-09']
        draft=self.ux.save(self.actor,self.payload)
        for locale in ('bg-BG','en-US'):
            result=self.run_case(draft,'booking',locale)
            self.assertEqual(result['verdict'],'PASS');self.assertEqual(result['booking_count'],1)
        self.assertEqual(self.store.count('appointments','demo'),0)

    def test_representative_preview_hours_and_no_slot(self):
        from semantic_os.backend.assistant.ux import Business
        for zone in ('Europe/Sofia','Pacific/Honolulu','Pacific/Kiritimati'):
            self.payload.business=Business(name='Synthetic',timezone=zone,opens='09:00',closes='12:00',holidays=['2030-10-09'])
            draft=self.ux.save(self.actor,self.payload)
            for locale in ('bg-BG','en-US'):
                for scenario in ('booking','rejection','ambiguous','occupied','short_confirmation'):
                    result=self.run_case(draft,scenario,locale)
                    self.assertEqual(result['verdict'],'PASS',(zone,locale,scenario))
                    self.assertIn('09:00',result['turns'][0]['input'])
        self.payload.business.closes='09:10'
        draft=self.ux.save(self.actor,self.payload)
        for locale in ('bg-BG','en-US'):
            result=self.run_case(draft,'booking',locale)
            self.assertEqual((result['verdict'],result['code'],result['booking_count']),('BLOCKED','preview_no_slot',0))
        self.assertEqual(self.store.count('appointments','demo'),0)

    def test_preview_unavailable_periods_and_legacy_draft(self):
        from semantic_os.backend.assistant.ux import Business
        self.payload.business=Business(name='Synthetic',unavailable_periods=[{'starts_at':'2030-10-09T00:00:00Z','ends_at':'2030-10-22T00:00:00Z'}])
        draft=self.ux.save(self.actor,self.payload)
        for locale in ('bg-BG','en-US'):self.assertEqual(self.run_case(draft,'booking',locale)['verdict'],'PASS')
        legacy=dict(draft);legacy['business']=dict(draft['business'])
        legacy['business'].pop('unavailable_periods');legacy['business'].pop('holidays')
        self.assertEqual(self.ux.simulate(legacy,RunInput(revision=1,scenario='booking',locale='en-US'))['verdict'],'PASS')
        self.assertEqual(self.store.count('appointments','demo'),0)

    def test_lifecycle_and_provider_preview_bilingual_isolated(self):
        self.payload.config.allowed_tools += ['RescheduleAppointment','CancelAppointment']
        draft=self.ux.save(self.actor,self.payload)
        tables=('appointments','jobs','conversations','messages','assistants','agents','usage_records')
        before={(tenant,table):self.store.list(table,tenant) for tenant in ('demo','other') for table in tables}
        for locale in ('bg-BG','en-US'):
            for scenario in ('reschedule','cancellation','out_of_hours','closed_day','unsupported','provider_failure','provider_uncertain'):
                result=self.run_case(draft,scenario,locale)
                self.assertEqual(result['verdict'],'PASS',(locale,scenario,result))
                self.assertTrue(all(result['checks'].values()))
                self.assertEqual(result['turns'][-1]['locale'],locale)
                if scenario in ('provider_failure','provider_uncertain'):
                    self.assertEqual(result['booking_count'],0)
                    self.assertNotIn('CreateAppointment',[row['tool'] for row in result['tools']])
                if scenario in ('reschedule','cancellation'):
                    self.assertEqual(result['booking_count'],1)
                    self.assertEqual(sum(row['tool']==('RescheduleAppointment' if scenario=='reschedule' else 'CancelAppointment') for row in result['tools']),1)
        for (tenant,table),rows in before.items():self.assertEqual(self.store.list(table,tenant),rows)

    def test_lifecycle_preview_permissions_and_missing_preconditions(self):
        from semantic_os.backend.assistant.ux import Business
        draft=self.ux.save(self.actor,self.payload)
        for locale in ('bg-BG','en-US'):
            for scenario in ('reschedule','cancellation'):
                result=self.run_case(draft,scenario,locale)
                self.assertEqual((result['verdict'],result['code'],result['booking_count']),('BLOCKED','tool_denied',0))
        self.payload.business=Business(name='Synthetic',weekdays=list(range(7)))
        draft=self.ux.save(self.actor,self.payload)
        for locale in ('bg-BG','en-US'):
            result=self.run_case(draft,'closed_day',locale)
            self.assertEqual((result['verdict'],result['code']),('BLOCKED','preview_no_closed_day'))
        self.payload.config.allowed_tools += ['RescheduleAppointment','CancelAppointment']
        draft=self.ux.save(self.actor,self.payload)
        modified=dict(draft);modified['agents']=[dict(row) for row in draft['agents']]
        for row in modified['agents']:
            if row['id']=='executor':row['allowed_tools']=['CheckAvailability','CreateAppointment']
        self.assertEqual(self.ux.simulate(modified,RunInput(revision=1,scenario='reschedule',locale='en-US'))['code'],'tool_denied')
        from semantic_os.backend.assistant.language import tr
        blocked=dict(draft);blocked['config']={**draft['config'],'allowed_tools':[]}
        for locale in ('bg-BG','en-US'):
            for scenario in ('provider_failure','provider_uncertain'):
                result=self.ux.simulate(blocked,RunInput(revision=1,scenario=scenario,locale=locale))
                self.assertEqual((result['verdict'],result['code']),('FAIL','tool_denied'))
                self.assertEqual(result['turns'][-1]['response'],tr(locale,'tool_denied'))
                self.assertIsNone(result['turns'][-1]['booking_status'])
        self.assertEqual(self.store.count('appointments','demo'),0)

    def test_preview_narrow_split_weekdays_and_fully_closed_window(self):
        from semantic_os.backend.assistant.ux import Business
        cases=[{'opens':'10:00','closes':'10:30'}, {'opens':'16:00','closes':'19:00','weekdays':[4]},
               {'opens':'09:00','closes':'12:00','unavailable_periods':[{'starts_at':'2030-10-09T06:00:00Z','ends_at':'2030-10-09T07:00:00Z'}]}]
        for fields in cases:
            self.payload.business=Business(name='Synthetic',**fields)
            draft=self.ux.save(self.actor,self.payload)
            for locale in ('bg-BG','en-US'):
                for scenario in ('booking','occupied'):
                    self.assertEqual(self.run_case(draft,scenario,locale)['verdict'],'PASS',fields)
        self.payload.business=Business(name='Synthetic',unavailable_periods=[{'starts_at':'2030-10-08T00:00:00Z','ends_at':'2030-10-24T00:00:00Z'}])
        draft=self.ux.save(self.actor,self.payload)
        for locale in ('bg-BG','en-US'):
            result=self.run_case(draft,'booking',locale)
            self.assertEqual((result['verdict'],result['code'],result['booking_count']),('BLOCKED','preview_no_slot',0))
        self.assertEqual(self.store.count('appointments','demo'),0)

    def test_preview_replay_is_idempotent_and_tenant_isolated(self):
        from unittest.mock import patch
        from semantic_os.backend.assistant.orchestration import Orchestrator
        original=Orchestrator.inbound
        def replay(engine,actor,identity,incoming):
            first=original(engine,actor,identity,incoming)
            repeated=original(engine,actor,identity,incoming)
            self.assertEqual(first['response'],repeated['response'])
            return first
        tables=('appointments','conversations','messages','jobs','assistants','agents','usage_records')
        before={(tenant,table):self.store.list(table,tenant) for tenant in ('demo','other') for table in tables}
        draft=self.ux.save(self.actor,self.payload)
        with patch.object(Orchestrator,'inbound',replay):
            for locale in ('bg-BG','en-US'):
                result=self.run_case(draft,'booking',locale)
                self.assertEqual((result['verdict'],result['booking_count']),('PASS',1))
                self.assertEqual(sum(tool['tool']=='CreateAppointment' for tool in result['tools']),1)
        for (tenant,table),rows in before.items():self.assertEqual(self.store.list(table,tenant),rows)

    def test_preview_dst_and_real_closed_day_refusal(self):
        from datetime import datetime, timezone
        from unittest.mock import patch
        from semantic_os.backend.assistant.calendar import MockCalendarProvider
        for month,day in ((3,28),(10,24)):
            class Reference(datetime):
                def __new__(cls,*args,**kwargs):
                    if args[:3]==(2030,10,8): return datetime(2030,month,day,9,tzinfo=timezone.utc)
                    return datetime(*args,**kwargs)
            self.payload.business.weekdays=[6]
            self.payload.business.opens='03:00';self.payload.business.closes='04:00'
            draft=self.ux.save(self.actor,self.payload)
            with patch('semantic_os.backend.assistant.ux.datetime',Reference):
                for locale in ('bg-BG','en-US'):
                    result=self.run_case(draft,'booking',locale)
                    self.assertEqual(result['verdict'],'PASS')
                    reference=datetime.fromisoformat(result['reference_at'])
                    self.assertEqual(reference.month,4 if month==3 else 11)
        tenant=self.store.tenant('demo');tenant['calendar_policy']={'holidays':['2030-10-09'],'weekdays':[0,1,2,3,4],'opens':'09:00','closes':'18:00','duration_minutes':30,'slot_minutes':1,'resources':[{'id':'synthetic'}]}
        self.store.update_tenant('demo',tenant)
        self.assertFalse(MockCalendarProvider(self.store).available('demo','2030-10-09T15:00:00+03:00',30))

    def test_concurrent_business_profile_change_invalidates_new_draft(self):
        draft=self.ux.save(self.actor,self.payload)
        tenant=self.store.tenant('demo');self.store.update_tenant('demo',{**tenant,'contact_email':'changed@example.invalid'})
        self.assertIn('business_config_changed',self.ux.readiness(self.actor,draft)['reasons'])

    def test_bilingual_scenarios_and_no_live_side_effects(self):
        draft = self.ux.save(self.actor, self.payload)
        before = {table:self.store.list(table,'demo') for table in ('assistants','appointments','conversations','messages','jobs','usage_records','agents')}
        for language in ('bg-BG','en-US'):
            for scenario in ('booking','short_confirmation','rejection','ambiguous','occupied','language_switch','handoff'):
                result = self.run_case(draft, scenario, language)
                self.assertEqual(result['verdict'], 'PASS', (language,scenario,result))
        for table, rows in before.items(): self.assertEqual(self.store.list(table,'demo'), rows, table)

    def test_audio_not_falsely_passed(self):
        draft = self.ux.save(self.actor,self.payload)
        self.assertTrue(all(row['verdict']=='NOT_RUN' for row in self.ux.readiness(self.actor,draft)['required_tests']))
        self.assertEqual(self.run_case(draft,'interruption')['verdict'],'BLOCKED')

    def test_occupied_preset_uses_the_tenant_relative_day(self):
        for zone in ('Europe/Sofia','Pacific/Honolulu','Pacific/Kiritimati'):
            self.payload.business.timezone=zone
            draft=self.ux.save(self.actor,self.payload)
            self.assertEqual(self.run_case(draft,'occupied')['verdict'],'PASS',zone)

    def test_draft_resume_revision_and_receipt_invalidation(self):
        draft=self.ux.save(self.actor,self.payload)
        self.run_case(draft,'booking')
        self.payload.revision=1; self.payload.step=4; self.payload.config.name='Changed'
        saved=self.ux.save(self.actor,self.payload,draft['id'])
        self.assertEqual(self.ux.draft(self.actor,draft['id'])['step'],4)
        self.assertNotEqual(saved['config_hash'],draft['config_hash'])
        self.assertFalse(self.ux.readiness(self.actor,saved)['can_publish'])
        with self.assertRaises(DomainError): self.ux.save(self.actor,self.payload,draft['id'])

    def test_cross_tenant_and_viewer_denied(self):
        draft=self.ux.save(self.actor,self.payload)
        other=self.store.principal('other','other')
        with self.assertRaises(DomainError): self.ux.draft(other,draft['id'])
        self.store.seed('demo','viewer','viewer')
        viewer=self.store.principal('viewer','demo')
        with self.assertRaises(DomainError): self.ux.save(viewer,self.payload)
        with self.assertRaises(DomainError): self.ux.test(viewer,draft['id'],RunInput(revision=1,scenario='booking',locale='bg-BG'))

    def test_permissions_enforced_in_sandbox(self):
        self.payload.config.allowed_tools=['CheckAvailability']
        draft=self.ux.save(self.actor,self.payload)
        result=self.run_case(draft,'booking')
        self.assertEqual(result['verdict'],'FAIL')
        self.assertEqual(result['booking_count'],0)
        self.assertEqual(self.store.count('appointments','demo'),0)

    def test_publish_requires_evidence_confirmation_and_preserves_source_draft(self):
        draft=self.ux.save(self.actor,self.payload)
        with self.assertRaises(DomainError): self.ux.publish(self.actor,draft['id'],ConfirmInput(revision=1,confirmed=True))
        for locale in ('bg-BG','en-US'):
            for scenario in ('booking','rejection','ambiguous'): self.run_case(draft,scenario,locale)
        self.assertTrue(self.ux.readiness(self.actor,draft)['can_publish'])
        with self.assertRaises(DomainError): self.ux.publish(self.actor,draft['id'],ConfirmInput(revision=1))
        created=self.ux.publish(self.actor,draft['id'],ConfirmInput(revision=1,confirmed=True))
        self.assertEqual(created['enabled_channels'],['web_chat'])
        self.assertEqual(self.ux.draft(self.actor,draft['id'])['status'],'published')
        self.assertEqual(self.store.count('appointments','demo'),0)
        self.assertEqual(self.ux.rows('demo','ux_version')[0]['target_assistant_id'],created['id'])

    def test_external_channels_and_live_llm_never_implicitly_activated(self):
        self.payload.config.enabled_channels=[Channel.WEB_CHAT,Channel.VOICE]
        self.payload.config.llm_provider='qwen'
        draft=self.ux.save(self.actor,self.payload)
        gates=self.ux.readiness(self.actor,draft)
        self.assertIn('voice_acceptance_blocked',gates['reasons'])
        self.assertIn('mock_test_not_live_proof',gates['reasons'])
        with self.assertRaises(DomainError): self.ux.publish(self.actor,draft['id'],ConfirmInput(revision=1,confirmed=True))

    def test_active_change_and_agent_change_block_promotion(self):
        self.payload.assistant_id='default'
        draft=self.ux.save(self.actor,self.payload)
        for locale in ('bg-BG','en-US'):
            for scenario in ('booking','rejection','ambiguous'): self.run_case(draft,scenario,locale)
        self.store.update('assistants','demo','default',{'name':'Concurrent change'})
        with self.assertRaises(DomainError): self.ux.publish(self.actor,draft['id'],ConfirmInput(revision=1,confirmed=True))
        self.store.update('agents','demo','executor',{'enabled':False})
        self.assertIn('agent_config_changed',self.ux.readiness(self.actor,draft)['reasons'])

    def test_business_and_pending_approval_block_promotion(self):
        draft=self.ux.save(self.actor,self.payload)
        for locale in ('bg-BG','en-US'):
            for scenario in ('booking','rejection','ambiguous'): self.run_case(draft,scenario,locale)
        self.store.update_tenant('demo',{**self.store.tenant('demo'),'timezone':'UTC'})
        self.assertIn('business_config_changed',self.ux.readiness(self.actor,draft)['reasons'])
        with self.assertRaises(DomainError): self.ux.publish(self.actor,draft['id'],ConfirmInput(revision=1,confirmed=True))

    def test_active_call_blocks_but_ended_call_allows_activation(self):
        draft=self.ux.save(self.actor,self.payload)
        for locale in ('bg-BG','en-US'):
            for scenario in ('booking','rejection','ambiguous'): self.run_case(draft,scenario,locale)
        call=self.store.add('call_sessions','demo',{'status':'listening'})
        with self.assertRaises(DomainError): self.ux.publish(self.actor,draft['id'],ConfirmInput(revision=1,confirmed=True))
        self.store.update('call_sessions','demo',call['id'],{'status':'ended'})
        self.assertEqual(self.ux.publish(self.actor,draft['id'],ConfirmInput(revision=1,confirmed=True))['name'],'Synthetic clinic')

    def test_overlapping_tests_report_busy_without_mutating_draft(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        entered,finish=Event(),Event()
        draft=self.ux.save(self.actor,self.payload)
        original=self.ux.simulate
        def slow(saved,payload):
            entered.set();finish.wait(5);return original(saved,payload)
        self.ux.simulate=slow
        with ThreadPoolExecutor(max_workers=1) as worker:
            future=worker.submit(self.run_case,draft,'booking')
            try:
                self.assertTrue(entered.wait(5))
                with self.assertRaises(DomainError) as error:self.run_case(draft,'booking')
                self.assertEqual(error.exception.code,'test_worker_busy')
                self.assertEqual(error.exception.status,429)
                self.assertEqual(self.ux.draft(self.actor,draft['id'])['revision'],1)
            finally:finish.set()
            self.assertEqual(future.result(timeout=5)['verdict'],'PASS')
        self.assertEqual(self.store.count('appointments','demo'),0)


class UXAPI(unittest.TestCase):
    def setUp(self):
        from datetime import datetime,timezone
        from types import SimpleNamespace
        from fastapi.testclient import TestClient
        from semantic_os.backend.assistant.api import create_app
        class Verifier:
            def verify(self, authorization):
                if authorization in ('Bearer other-fixture','Bearer viewer-fixture','Bearer operator-fixture'):
                    return SimpleNamespace(subject=authorization.split()[1].split('-')[0])
                raise DomainError('unauthorized',401)
        self.store=Store();self.store.seed();self.store.seed('other','other');self.store.seed('demo','viewer','viewer');self.store.seed('demo','operator','operator')
        self.app=create_app(store=self.store,providers=ProviderRegistry(),demo_enabled=True,demo_token='synthetic-ux-fixture',verifier=Verifier(),clock=lambda:datetime(2030,10,8,9,tzinfo=timezone.utc))
        self.client=TestClient(self.app)
        self.headers={'Authorization':'Bearer synthetic-ux-fixture','X-Tenant-ID':'demo'}
        self.payload=DraftInput(config=AssistantConfig(name='Synthetic clinic',enabled_channels=['web_chat'],allowed_tools=['CheckAvailability','CreateAppointment','EscalateToHuman']),business={'name':'Synthetic clinic'}).model_dump(mode='json')

    def tearDown(self):
        self.client.close();self.app.state.voice_runtime.shutdown();self.store.close()

    def test_setup_http_validation_revision_cancel_and_no_activation(self):
        bad={**self.payload,'business':{**self.payload['business'],'timezone':'invalid/timezone'}}
        self.assertEqual(self.client.post('/api/ux/drafts',headers=self.headers,json=bad).status_code,422)
        draft=self.client.post('/api/ux/drafts',headers=self.headers,json=self.payload).json()
        self.assertEqual(self.client.get('/api/ux/drafts',headers=self.headers).json()[0]['id'],draft['id'])
        self.assertEqual(self.client.put('/api/ux/drafts/'+draft['id'],headers=self.headers,json=self.payload).status_code,409)
        path='/api/ux/drafts/'+draft['id']+'/cancel'
        self.assertEqual(self.client.post(path,headers=self.headers,json={'revision':1,'confirmed':False}).status_code,403)
        self.assertEqual(self.client.post(path,headers=self.headers,json={'revision':1,'confirmed':True}).status_code,200)
        self.assertEqual(self.store.count('assistants','demo'),1)
        self.assertEqual(self.store.count('appointments','demo'),0)

    def test_http_tenant_and_viewer_boundaries(self):
        draft=self.client.post('/api/ux/drafts',headers=self.headers,json=self.payload).json()
        path='/api/ux/drafts/'+draft['id']+'/tests'
        payload={'revision':1,'scenario':'booking','locale':'bg-BG'}
        other={'Authorization':'Bearer other-fixture','X-Tenant-ID':'other'}
        viewer={'Authorization':'Bearer viewer-fixture','X-Tenant-ID':'demo'}
        self.assertEqual(self.client.post(path,headers=other,json=payload).status_code,404)
        self.assertEqual(self.client.post(path,headers=viewer,json=payload).status_code,403)
        self.assertEqual(self.client.get('/api/ux/drafts',headers=viewer).status_code,403)

    def test_diagnostic_privacy_order_and_actual_booking(self):
        conversation=self.client.post('/api/conversations',headers=self.headers,json={}).json()['id']
        for index,content in enumerate(['Book an appointment tomorrow at 15:00.','My name is John Smith.','Yes, confirm.']):
            response=self.client.post(f'/api/conversations/{conversation}/messages',headers=self.headers,json={'content':content,'event_id':f'ux-{index}','locale':'en-US'})
            self.assertEqual(response.status_code,200,response.text)
        result=self.client.get(f'/api/ux/conversations/{conversation}/diagnostics',headers=self.headers)
        self.assertEqual(result.status_code,200,result.text)
        data=result.json();self.assertEqual(len(data['appointments']),1)
        self.assertEqual(data['voice_coverage'],'not_applicable')
        self.assertEqual(data['booking_status'],'completed')
        self.assertNotIn('John Smith',result.text)
        self.assertNotIn('arguments',result.text)
        operator={'Authorization':'Bearer operator-fixture','X-Tenant-ID':'demo'}
        self.assertEqual(self.client.get(f'/api/ux/conversations/{conversation}/diagnostics',headers=operator).status_code,200)
        dates=[event['timestamp'] for event in data['timeline'] if event['timestamp']]
        self.assertEqual(dates,sorted(dates))
        other={'Authorization':'Bearer other-fixture','X-Tenant-ID':'other'}
        self.assertEqual(self.client.get(f'/api/ux/conversations/{conversation}/diagnostics',headers=other).status_code,404)

    def test_inbox_cursor_filters_timezone_and_no_cross_tenant_join(self):
        for index in range(6):
            row=self.app.state.orchestrator.conversation(self.store.principal('demo-admin','demo'),'default')
            self.store.update('conversations','demo',row['id'],{'status':'closed' if index%2 else 'open'})
            self.store.add('messages','demo',{'conversation_id':row['id'],'content':'Synthetic','timestamp':'2030-10-08T22:30:00+00:00'})
        path='/api/inbox?limit=2&status=open&local_day=2030-10-09'
        first=self.client.get(path,headers=self.headers).json()
        self.assertEqual(len(first['items']),2)
        second=self.client.get(path+'&cursor='+str(first['next_cursor']),headers=self.headers).json()
        self.assertEqual(len(second['items']),1)
        self.assertFalse({row['id'] for row in first['items']} & {row['id'] for row in second['items']})
        self.assertIsNone(second['next_cursor'])
        self.assertEqual(self.client.get('/api/inbox?limit=101',headers=self.headers).status_code,422)
        self.assertEqual(self.client.get('/api/inbox?cursor=1',headers=self.headers).status_code,422)
        self.assertEqual(self.client.get('/api/inbox?local_day=2030-10-08',headers=self.headers).json(),[])
        other={'Authorization':'Bearer other-fixture','X-Tenant-ID':'other'}
        self.assertEqual(self.client.get('/api/inbox?limit=2',headers=other).json()['items'],[])

    def test_last_message_uses_reception_order_for_equal_timestamps(self):
        conversation=self.app.state.orchestrator.conversation(self.store.principal('demo-admin','demo'),'default')
        for text in ('Earlier','Latest'):
            self.store.add('messages','demo',{'conversation_id':conversation['id'],'content':text,'timestamp':'2030-10-08T09:00:00+00:00'})
        row=self.client.get('/api/inbox?conversation_id='+conversation['id'],headers=self.headers).json()[0]
        self.assertEqual(row['last_message'],'Latest')

    def test_last_message_compares_instants_across_timezones(self):
        conversation=self.app.state.orchestrator.conversation(self.store.principal('demo-admin','demo'),'default')
        for text,at in [('Earlier','2030-10-08T20:00:00+02:00'),('Latest','2030-10-08T19:00:00+00:00')]:
            self.store.add('messages','demo',{'conversation_id':conversation['id'],'content':text,'timestamp':at})
        row=self.client.get('/api/inbox?conversation_id='+conversation['id'],headers=self.headers).json()[0]
        self.assertEqual(row['last_message'],'Latest')

    def test_http_publish_and_version_metadata_do_not_expose_config(self):
        self.payload['config']['instructions']='Synthetic private instructions'
        draft=self.client.post('/api/ux/drafts',headers=self.headers,json=self.payload).json()
        for locale in ('bg-BG','en-US'):
            for scenario in ('booking','rejection','ambiguous'):
                response=self.client.post('/api/ux/drafts/'+draft['id']+'/tests',headers=self.headers,json={'revision':1,'scenario':scenario,'locale':locale})
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['verdict'],'PASS')
        response=self.client.post('/api/ux/drafts/'+draft['id']+'/publish',headers=self.headers,json={'revision':1,'confirmed':True})
        self.assertEqual(response.status_code,200,response.text)
        identity=response.json()['id']
        summary=self.client.get('/api/ux/assistants/'+identity+'/summary',headers=self.headers)
        self.assertEqual(len(summary.json()['versions']),1)
        self.assertNotIn('Synthetic private instructions',summary.text)
        self.assertFalse(summary.json()['rollback_supported'])
