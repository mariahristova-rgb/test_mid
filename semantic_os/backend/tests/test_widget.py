"""Widget capabilities, immutable snapshots and confirmed demo booking boundaries."""
from datetime import datetime,timedelta,timezone
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from fastapi.testclient import TestClient
from semantic_os.backend.assistant.api import create_app
from semantic_os.backend.assistant.domain import AssistantConfig,DomainError
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.ux import DraftInput,RunInput,ConfirmInput
from semantic_os.backend.assistant.widget import WidgetSettings,WidgetPublish,WidgetAction,Redeem,WidgetMessage


class WidgetTests(unittest.TestCase):
    def setUp(self):
        self.environment=patch.dict('os.environ',{'WIDGET_PUBLIC_ORIGIN':'http://127.0.0.1:3020','WIDGET_DEMO_SITE_ORIGINS':'http://127.0.0.1:3021'})
        self.environment.start()
        self.store=Store();self.store.seed();self.store.seed('other','other')
        self.now=datetime(2030,10,8,9,tzinfo=timezone.utc)
        self.app=create_app(store=self.store,demo_enabled=True,demo_token='synthetic-widget-staff',clock=lambda:self.now)
        self.client=TestClient(self.app)
        self.actor=self.store.principal('demo-admin','demo')
        self.staff={'Authorization':'Bearer synthetic-widget-staff','X-Tenant-ID':'demo'}
        self.widget=self.app.state.widget
        self.site='http://127.0.0.1:3021'
        self.draft=self.app.state.ux.save(self.actor,DraftInput(assistant_id='default',config=AssistantConfig(name='Fictional',instructions='Use approved business information.',enabled_channels=['web_chat'],allowed_tools=['CheckAvailability','CreateAppointment','EscalateToHuman']),business={'name':'Fictional'}))
        for locale in ('bg-BG','en-US'):
            for scenario in ('booking','rejection','ambiguous'):
                self.app.state.ux.test(self.actor,self.draft['id'],RunInput(revision=1,scenario=scenario,locale=locale))
        self.app.state.ux.publish(self.actor,self.draft['id'],ConfirmInput(revision=1,confirmed=True))
        settings=WidgetSettings(assistant_id='default',origins=[self.site],greetings={'bg-BG':'Здравейте.','en-US':'Hello.'},privacy_notices={'bg-BG':'Демо чат.','en-US':'Demo chat.'})
        self.integration=self.widget.configure(self.actor,settings)
        proof=self.widget.challenge(self.actor,self.integration['id'],self.site)
        self.widget.fetch_domain=lambda *_:proof['content']
        self.widget.verify(self.actor,self.integration['id'],self.site)
        self.widget.publish(self.actor,self.integration['id'],WidgetPublish(draft_id=self.draft['id'],confirmed=True))
        self.public_id=self.integration['public_id']

    def tearDown(self):
        self.client.close();self.app.state.voice_runtime.shutdown();self.store.close();self.environment.stop()

    def visitor(self,locale='bg-BG'):
        admission=self.widget.ticket(self.public_id,self.site)
        return self.widget.redeem(self.public_id,Redeem(ticket=admission['ticket'],parent_origin=self.site,locale=locale))['session_token']

    def send(self,token,text,event,locale='bg-BG'):
        return self.widget.message(self.public_id,token,WidgetMessage(content=text,event_id=event,locale=locale))

    def enable_analytics(self):
        settings=WidgetSettings.model_validate(self.integration['settings']).model_copy(update={'analytics_enabled':True})
        self.widget.configure(self.actor,settings,self.integration['id'])
        self.widget.publish(self.actor,self.integration['id'],WidgetPublish(draft_id=self.draft['id'],confirmed=True))

    def test_optional_analytics_require_owner_enablement_and_explicit_visitor_consent(self):
        token=self.visitor()
        headers={'Authorization':'Bearer '+token,'Origin':'http://127.0.0.1:3020'}
        url='/widget/analytics-consent/'+self.public_id
        self.assertEqual(self.client.post(url,headers=headers,json={'allowed':True}).status_code,403)
        self.assertEqual(self.widget.rows('demo','journey_event'),[])
        self.enable_analytics();token=self.visitor();headers['Authorization']='Bearer '+token
        self.assertEqual(self.client.post(url,headers=headers,json={'allowed':'true'}).status_code,422)
        self.assertEqual(self.client.post(url,headers=headers,json={'allowed':True}).status_code,200)
        self.assertEqual(self.client.post(url,headers=headers,json={'allowed':True}).status_code,200)
        self.send(token,'Здравейте','consent-event');self.send(token,'Здравейте','consent-event')
        rows=self.widget.rows('demo','journey_event')
        self.assertEqual(sorted(r['stage'] for r in rows),['conversation_started','opted_in_opened'])
        self.assertNotIn('Здравейте',json.dumps(rows,ensure_ascii=False));self.assertNotIn(token,json.dumps(rows))
        self.assertEqual(self.client.post(url,headers=headers,json={'allowed':False}).status_code,200)
        self.assertTrue(all(r.get('redacted') for r in self.widget.rows('demo','journey_event')))

    def test_analytics_withdrawal_survives_session_expiry_and_erasure_purges_evidence(self):
        self.enable_analytics();token=self.visitor()
        headers={'Authorization':'Bearer '+token,'Origin':'http://127.0.0.1:3020'}
        url='/widget/analytics-consent/'+self.public_id
        self.client.post(url,headers=headers,json={'allowed':True})
        self.now+=timedelta(minutes=11)
        self.assertEqual(self.client.post(url,headers=headers,json={'allowed':False}).status_code,200)
        self.assertEqual(self.client.post(url,headers=headers,json={'allowed':True}).status_code,401)
        self.assertEqual(self.app.state.customer_workspace.analytics(self.actor,30)['funnel'],[])

    def test_analytics_observer_cannot_restore_withdrawn_consent_from_stale_session(self):
        self.enable_analytics();token=self.visitor()
        headers={'Authorization':'Bearer '+token,'Origin':'http://127.0.0.1:3020'}
        url='/widget/analytics-consent/'+self.public_id
        self.client.post(url,headers=headers,json={'allowed':True})
        row,snapshot,_=self.widget.session(self.public_id,token)
        self.client.post(url,headers=headers,json={'allowed':False})
        self.widget.journey.observe(row,snapshot,{'human_requested':True})
        self.assertTrue(all(r.get('redacted') for r in self.widget.rows('demo','journey_event')))

    def test_bilingual_runtime_booking_and_duplicate_confirmation(self):
        for index,locale in enumerate(('bg-BG','en-US')):
            token=self.visitor(locale)
            texts=[('Искам да запиша час за утре в 15:00.','Казвам се Иван Иванов.','Да, потвърждавам.'),('Book an appointment tomorrow at 16:00.','My name is John Smith.','Yes, confirm.')][index]
            for turn,text in enumerate(texts): result=self.send(token,text,f'e{turn}',locale)
            self.assertEqual(result['booking_status'],'completed')
            repeated=self.send(token,texts[-1],'e2',locale)
            self.assertTrue(repeated['duplicate'])
        self.assertEqual(self.store.count('appointments','demo'),2)
        self.assertEqual(self.store.count('appointments','other'),0)
        self.assertTrue(self.store.list('agent_executions','demo'))

    def test_public_ids_and_visitor_tokens_cannot_read_staff_configuration(self):
        token=self.visitor()
        self.assertEqual(self.client.get('/api/assistants',headers={'Authorization':'Bearer '+token,'X-Tenant-ID':'demo'}).status_code,401)
        self.assertEqual(self.client.get('/api/widgets',headers={'Authorization':'Bearer '+self.public_id,'X-Tenant-ID':'demo'}).status_code,401)
        self.assertNotIn('instructions',json.dumps(self.widget.redeem(self.public_id,Redeem(ticket=self.widget.ticket(self.public_id,self.site)['ticket'],parent_origin=self.site,locale='en-US'))))

    def test_ticket_replay_expiry_and_wrong_parent(self):
        admission=self.widget.ticket(self.public_id,self.site)
        with self.assertRaises(DomainError):self.widget.redeem(self.public_id,Redeem(ticket=admission['ticket'],parent_origin='https://evil.example',locale='bg-BG'))
        payload=Redeem(ticket=admission['ticket'],parent_origin=self.site,locale='bg-BG')
        self.widget.redeem(self.public_id,payload)
        with self.assertRaises(DomainError):self.widget.redeem(self.public_id,payload)
        another=self.widget.ticket(self.public_id,self.site)
        self.now+=timedelta(seconds=61)
        with self.assertRaises(DomainError):self.widget.redeem(self.public_id,Redeem(ticket=another['ticket'],parent_origin=self.site,locale='bg-BG'))

    def test_session_expiry_unpublish_and_revocation(self):
        token=self.visitor();self.now+=timedelta(minutes=11)
        with self.assertRaises(DomainError):self.send(token,'Здравейте.','expired')
        self.now-=timedelta(minutes=11);token=self.visitor()
        self.widget.lifecycle(self.actor,self.integration['id'],'unpublish',WidgetAction(confirmed=True))
        with self.assertRaises(DomainError):self.send(token,'Здравейте.','unpublished')
        version=self.widget.rows('demo','widget_version')[0]
        self.widget.lifecycle(self.actor,self.integration['id'],'rollback',WidgetAction(confirmed=True,version_id=version['id']))
        with self.assertRaises(DomainError):self.send(token,'Здравейте.','old-epoch')
        self.widget.lifecycle(self.actor,self.integration['id'],'revoke',WidgetAction(confirmed=True))
        with self.assertRaises(DomainError):self.widget.ticket(self.public_id,self.site)
        with self.assertRaises(DomainError):self.widget.challenge(self.actor,self.integration['id'],self.site)

    def test_snapshot_does_not_follow_legacy_instruction_edits(self):
        token=self.visitor()
        self.store.update('assistants','demo','default',{'instructions':'Changed staff-only instructions','allowed_tools':['SendMessage']})
        self.send(token,'Искам да запиша час за утре в 15:00.','book')
        result=self.send(token,'Казвам се Иван Иванов.','name')
        self.assertEqual(result['booking_status'],'awaiting_confirmation')
        result=self.send(token,'Да, потвърждавам.','confirm')
        self.assertEqual(result['booking_status'],'completed')

    def test_origin_cors_and_iframe_policy(self):
        path='/widget/admission/'+self.public_id
        for invalid in ('https://evil.example','null',''):
            self.assertEqual(self.client.post(path,headers={'Origin':invalid},json={'locale':'auto'}).status_code,403)
        response=self.client.options(path,headers={'Origin':self.site,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Content-Type'})
        self.assertEqual(response.status_code,204)
        self.assertEqual(response.headers['access-control-allow-origin'],self.site)
        response=self.client.get('/widget/frame/'+self.public_id,params={'parent_origin':self.site})
        self.assertEqual(response.status_code,200,response.text)
        self.assertNotIn('x-frame-options',response.headers)
        self.assertIn('frame-ancestors '+self.site,response.headers['content-security-policy'])
        self.assertEqual(self.client.get('/api/bootstrap',headers=self.staff).headers['x-frame-options'],'DENY')

    def test_no_arbitrary_tool_fields_or_tenant_selection(self):
        token=self.visitor()
        response=self.client.post('/widget/messages/'+self.public_id,headers={'Origin':'http://127.0.0.1:3020','Authorization':'Bearer '+token,'X-Tenant-ID':'other'},json={'content':'Hello','event_id':'bad','locale':'en-US','tool':'SendMessage'})
        self.assertEqual(response.status_code,422)
        response=self.client.post('/widget/messages/'+self.public_id,headers={'Origin':'http://127.0.0.1:3020','Authorization':'Bearer '+token,'X-Tenant-ID':'other'},json={'content':'Hello','event_id':'good','locale':'en-US'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.store.count('conversations','other'),0)

    def test_domain_change_and_shared_agent_change_invalidate_sessions(self):
        token=self.visitor()
        self.store.update('agents','demo','executor',{'enabled':False})
        with self.assertRaises(DomainError):self.send(token,'Здравейте.','changed')

    def test_clear_and_retention_leave_appointments_intact(self):
        token=self.visitor()
        for index,text in enumerate(['Искам да запиша час за утре в 15:00.','Казвам се Иван Иванов.','Да, потвърждавам.']):self.send(token,text,str(index))
        self.widget.clear(self.public_id,token)
        self.assertEqual(self.store.count('appointments','demo'),1)
        self.assertTrue(all(not row['content'] for row in self.store.list('messages','demo')))
        with self.assertRaises(DomainError):self.send(token,'Здравейте.','after-clear')
        self.now+=timedelta(days=8)
        self.widget.purge()
        self.assertTrue(all(row['status']=='purged' for row in self.widget.rows('demo','widget_session')))

    def test_clear_and_retention_redact_traces_only_for_owned_conversation(self):
        for cleanup in ('clear','purge'):
            with self.subTest(cleanup=cleanup):
                token=self.visitor()
                _,session,_=self.widget.session(self.public_id,token)
                conversation=session['conversation_id']
                self.store.add('conversations','other',{'assistant_id':'default','status':'open'},id=conversation)
                unrelated=self.store.add('conversations','demo',{'assistant_id':'default','status':'open'})['id']
                targets=[]
                untouched=[]
                for table in ('agent_executions','tool_executions','approvals'):
                    data={'conversation_id':conversation,'status':'pending','arguments':{'name':'Sensitive visitor'},
                          'result':{'text':'Sensitive visitor'},'handoff':{'arguments':{'name':'Sensitive visitor'}}}
                    targets.append((table,self.store.add(table,'demo',data)))
                    untouched.append((table,self.store.add(table,'other',data)))
                    untouched.append((table,self.store.add(table,'demo',{**data,'conversation_id':unrelated})))
                appointment=self.store.add('appointments','demo',{'conversation_id':conversation,'contact_name':'Retained booking','status':'confirmed'})
                if cleanup=='clear':
                    self.widget.clear(self.public_id,token)
                    self.assertTrue(self.widget.clear(self.public_id,token)['cleared'])
                else:
                    self.now+=timedelta(days=8)
                    self.widget.purge()
                for table,original in targets:
                    actual=self.store.get(table,'demo',original['id'])
                    self.assertTrue(actual['redacted'])
                    for field in ('arguments','result','outcome','handoff'):self.assertEqual(actual[field],{})
                    if table=='approvals':self.assertEqual(actual['status'],'cancelled')
                for table,original in untouched:self.assertEqual(self.store.get(table,original['tenant_id'],original['id']),original)
                self.assertEqual(self.store.get('appointments','demo',appointment['id']),appointment)

    def test_clear_and_retention_remove_uncommitted_booking_memory(self):
        for cleanup in ('clear','purge'):
            token=self.visitor('en-US')
            self.send(token,'Book an appointment tomorrow at 15:00.','request-'+cleanup,'en-US')
            self.send(token,'My name is Synthetic Visitor.','details-'+cleanup,'en-US')
            _,session,_=self.widget.session(self.public_id,token)
            self.assertTrue(self.store.get('conversations','demo',session['conversation_id'])['booking_state']['contact_name'])
            if cleanup=='clear':self.widget.clear(self.public_id,token)
            else:self.now+=timedelta(days=8);self.widget.purge()
            self.assertIsNone(self.store.get('conversations','demo',session['conversation_id']).get('booking_state'))
        self.assertEqual(self.store.count('appointments','demo'),0)

    def test_limits_and_payload_replay_do_not_recharge(self):
        row=self.widget.get(self.actor,self.integration['id'])
        self.store.update('operations_events','demo',row['id'],{'settings':{**row['settings'],'daily_sessions':1,'daily_messages':10}})
        token=self.visitor()
        with self.assertRaises(DomainError) as error:self.visitor()
        self.assertEqual(error.exception.status,429)
        self.send(token,'Hello','same','en-US')
        self.send(token,'Hello','same','en-US')
        with self.assertRaises(DomainError):self.send(token,'Changed','same','en-US')
        for index in range(9):self.send(token,'Hello',str(index),'en-US')
        with self.assertRaises(DomainError) as error:self.send(token,'Hello','over','en-US')
        self.assertEqual(error.exception.status,429)

    def test_deletion_remains_available_after_revocation(self):
        token=self.visitor();self.send(token,'Hello','one','en-US')
        self.widget.lifecycle(self.actor,self.integration['id'],'revoke',WidgetAction(confirmed=True))
        self.now+=timedelta(minutes=11)
        self.assertTrue(self.widget.clear(self.public_id,token)['cleared'])
        self.assertTrue(all(not row['content'] for row in self.store.list('messages','demo')))

    def test_changed_business_policy_requires_retesting(self):
        tenant=self.store.tenant('demo');tenant['timezone']='UTC';self.store.update_tenant('demo',tenant)
        with self.assertRaises(DomainError):self.widget.publish(self.actor,self.integration['id'],WidgetPublish(draft_id=self.draft['id'],confirmed=True))

    def test_logo_and_origin_injection_are_rejected(self):
        from pydantic import ValidationError
        from semantic_os.backend.assistant.widget import origin,domain_file
        for value in ('https://*.example.com',"https://example.com/'script",'javascript:alert(1)','https://127.0.0.1','https://example.com;script-src'):
            with self.assertRaises(ValueError):origin(value)
        with self.assertRaises(ValidationError):WidgetSettings(assistant_id='default',origins=[self.site],logo_url='javascript:alert(1)',greetings={'bg-BG':'Hi','en-US':'Hi'},privacy_notices={'bg-BG':'Demo','en-US':'Demo'})
        with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('10.0.0.1',443))]):
            with self.assertRaises(DomainError):domain_file('https://private.example','wdg_test',set())

    def test_approved_faq_detection_and_plain_text_xss(self):
        from semantic_os.backend.assistant.language import LanguageResolver
        self.assertEqual(LanguageResolver().detect('What are your opening hours?')[0],'en-US')
        token=self.visitor('en-US')
        self.send(token,'<script>alert(1)</script>','plain','en-US')
        self.assertTrue(any(row['content']=='<script>alert(1)</script>' for row in self.store.list('messages','demo')))
        self.assertNotIn('script',self.widget.message(self.public_id,token,WidgetMessage(content='Hello',event_id='next',locale='en-US'))['response'].lower())
