"""Two-agent customer Google bridge; all provider traffic is MockTransport."""
from datetime import datetime, timedelta, timezone
import json
import unittest
import httpx
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from semantic_os.backend.assistant.store import Store, uid
from semantic_os.backend.assistant.security import TenantSecretStore
from semantic_os.backend.assistant.customer_oauth import CustomerOAuthService
from semantic_os.backend.assistant.connector_adapters import OfflineProviderHTTP, required_scopes
from semantic_os.backend.assistant.connector_contracts import PlatformOAuthApplication, CustomerConnectionConfig
from semantic_os.backend.assistant.api import create_app


class CustomerBookingTests(unittest.TestCase):
    def setUp(self):
        self.store=Store();self.store.seed();self.store.seed('other','other')
        self.now=datetime(2026,10,14,9,tzinfo=timezone.utc)
        self.events={};self.posts=0;self.fail_after_write=False;self.malformed_after_write=False;self.calls=[]
        self.key=Fernet.generate_key().decode();self.actor=self.store.principal('demo-admin','demo')
        self.store.update_tenant('demo',{**self.store.tenant('demo'),'calendar_policy':{'weekdays':[0,1,2,3,4], 'opens':'09:00','closes':'18:00',
            'duration_minutes':30,'slot_minutes':30,'resources':[{'id':'calendar-owner'}], 'service_id':'consultation',
            'buffer_minutes':15,'notice_minutes':60,'holidays':[],'unavailable_periods':[]}})
        app=PlatformOAuthApplication(provider='google',client_id='synthetic-client',secret_reference='platform:oauth:google:client_secret',
            redirect_uri='https://staging.example.invalid/backend/api/connectors/oauth/google/callback',
            allowed_redirects=['https://staging.example.invalid/backend/api/connectors/oauth/google/callback'])
        def handle(request):
            self.calls.append((request.method,request.url.path))
            if request.url.host=='oauth2.googleapis.com':
                return httpx.Response(200,json={'access_token':'synthetic-access','refresh_token':'synthetic-refresh',
                    'scope':' '.join(required_scopes('google',['availability','create'])),'expires_in':3600})
            if request.url.path.endswith('/calendarList'):
                return httpx.Response(200,json={'items':[{'id':'calendar-owner','accessRole':'owner'}]})
            if request.url.path.endswith('/freeBusy'):
                return httpx.Response(200,json={'calendars':{'calendar-owner':{'busy':[]}}})
            if request.url.path.endswith('/events') and request.method=='POST':
                self.posts+=1;event=json.loads(request.content);self.events[event['id']]=event
                if self.fail_after_write:raise httpx.ReadTimeout('synthetic uncertain write')
                if self.malformed_after_write:return httpx.Response(201,content=b'not-json')
                return httpx.Response(201,json=event)
            if '/events/' in request.url.path and request.method=='GET':
                event=self.events.get(request.url.path.rsplit('/',1)[1])
                return httpx.Response(200 if event else 404,json=event or {})
            raise AssertionError('Unexpected synthetic request')
        opts={'applications':[app],'http':OfflineProviderHTTP(httpx.MockTransport(handle)),
              'platform_secret':lambda ref:'synthetic-secret','verify_identity':lambda *args:'synthetic-account'}
        service=CustomerOAuthService(self.store,TenantSecretStore(self.store,self.key),clock=lambda:self.now,**opts)
        row=service.create(self.actor,CustomerConnectionConfig(provider='google',actions=['availability','create'],revision=1))
        started=service.start(self.actor,row['id'],1)
        connected=service.complete(self.actor,row['id'],'google',started['state'],started['binding'],'synthetic-code')
        selected=service.select_resources(self.actor,row['id'],connected['revision'],['calendar-owner'])
        self.connection=selected
        self.app=create_app(store=self.store,demo_enabled=True,demo_token='synthetic-booking-token',encryption_key=self.key,
            clock=lambda:self.now,customer_oauth_options=opts,customer_calendar_bindings={'demo':{'subject':'demo-admin','connection_id':row['id']}})
        self.client=TestClient(self.app)
        self.headers={'Authorization':'Bearer synthetic-booking-token','X-Tenant-ID':'demo'}

    def tearDown(self):
        self.client.close();self.store.close()

    def send(self,conversation,text,event=None):
        response=self.client.post('/api/conversations/'+conversation+'/messages',headers=self.headers,
            json={'content':text,'event_id':event or uid()})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    def queue(self,locale='bg-BG'):
        conversation=self.client.post('/api/conversations',headers=self.headers,json={}).json()['id']
        first=self.send(conversation,'Здравейте, искам да запиша час за утре в 15:00.' if locale=='bg-BG' else 'Hello, I would like to book an appointment for tomorrow at 15:00.')
        self.assertEqual(first['booking_status'],'need_name');self.assertEqual(self.posts,0)
        self.send(conversation,'Казвам се Иван Иванов.' if locale=='bg-BG' else 'My name is John Smith.')
        self.assertEqual(self.posts,0)
        event=uid();confirmed=self.send(conversation,'Да, потвърждавам.' if locale=='bg-BG' else 'Yes, confirm.',event)
        self.assertEqual(confirmed['outcome']['code'],'appointment_pending');self.assertEqual(self.posts,0)
        self.send(conversation,'Да, потвърждавам.' if locale=='bg-BG' else 'Yes, confirm.',event)
        self.assertEqual(len([j for j in self.store.list('jobs','demo') if j.get('kind')=='customer_calendar_create']),1)
        return conversation

    def test_bulgarian_two_agent_confirmation_queue_and_provider_booking(self):
        conversation=self.queue();self.app.state.customer_booking.worker();self.app.state.customer_booking.worker()
        self.assertEqual(self.posts,1)
        appointments=self.store.list('appointments','demo');self.assertEqual(appointments[0]['status'],'confirmed')
        self.assertEqual(appointments[0]['timezone'],'Europe/Sofia')
        messages=self.store.list('messages','demo')
        self.assertTrue(any(m.get('conversation_id')==conversation and 'Часът е потвърден' in m.get('content','') for m in messages))
        self.assertEqual(self.store.list('appointments','other'),[])

    def test_english_unknown_write_reconciles_without_second_post(self):
        self.queue('en-US');self.fail_after_write=True;self.app.state.customer_booking.worker()
        self.assertEqual(self.posts,1);self.assertEqual(self.store.list('appointments','demo')[0]['status'],'uncertain_external')
        self.now+=timedelta(seconds=61);self.app.state.customer_booking.worker();self.assertEqual(self.posts,1)
        self.assertEqual(self.store.list('appointments','demo')[0]['status'],'confirmed')
        self.assertTrue(any('Appointment confirmed' in m.get('content','') for m in self.store.list('messages','demo')))

    def test_disconnect_before_worker_prevents_provider_write(self):
        self.queue();self.app.state.customer_oauth.disconnect(self.actor,self.connection['id'],self.connection['revision'])
        self.app.state.customer_booking.worker();self.assertEqual(self.posts,0)
        self.assertEqual(self.store.list('appointments','demo')[0]['status'],'cancelled')

    def test_closed_day_never_uses_fixture_slots_as_provider_success(self):
        bridge=self.app.state.customer_booking
        self.assertFalse(bridge.available('demo','2026-10-18T15:00:00+03:00',30))
        self.assertFalse(bridge.available('demo','2026-10-15T20:00:00+03:00',30))
        self.assertEqual(self.posts,0)

    def test_explicit_activation_snapshots_policy_and_refuses_missing_consent(self):
        from semantic_os.backend.assistant.domain import DomainError
        bridge=self.app.state.customer_booking
        with self.assertRaises(DomainError):bridge.configure(self.actor,self.connection['id'],self.connection['revision'],False)
        configured=bridge.configure(self.actor,self.connection['id'],self.connection['revision'],True)
        self.assertTrue(configured['booking_enabled'])
        tenant=self.store.tenant('demo');self.store.update_tenant('demo',{**tenant,'calendar_policy':{**tenant['calendar_policy'],'opens':'16:00'}})
        self.assertTrue(bridge.available('demo','2026-10-15T15:00:00+03:00',30))
        self.assertEqual(self.posts,0)
    def test_default_disabled_oauth_settings_do_not_read_secrets_or_construct_transport(self):
        from unittest.mock import patch
        from semantic_os.backend.assistant.customer_oauth_settings import customer_oauth_environment
        with patch.dict('os.environ',{'ASSISTANT_CUSTOMER_OAUTH_ENABLED':'false'}),patch('semantic_os.backend.assistant.connector_adapters.ProductionProviderHTTP',side_effect=AssertionError('must stay disabled')):
            self.assertEqual(customer_oauth_environment(),{})

    def test_queued_authorization_is_not_counted_as_a_completed_business_outcome(self):
        from semantic_os.backend.assistant.journey import Journey
        conversation=self.queue()
        job=next(j for j in self.store.list('jobs','demo') if j.get('kind')=='customer_calendar_create')
        stages=[];journey=Journey(self.store,lambda:self.now);journey.record=lambda row,session,stage,scope:stages.append(stage)
        journey.observe({'tenant_id':'demo'},{'analytics_allowed':True,'conversation_id':conversation},{'correlation_id':job['correlation_id'],'booking_status':'completed'})
        self.assertNotIn('calendar_created',stages)

    def test_dst_day_skips_ambiguous_wall_times_without_hiding_valid_slots(self):
        self.now=datetime(2026,10,24,9,tzinfo=timezone.utc)
        tenant=self.store.tenant('demo');policy={**tenant['calendar_policy'],'weekdays':[6],'opens':'02:00','closes':'05:00'}
        self.store.update_tenant('demo',{**tenant,'calendar_policy':policy})
        slots=self.app.state.customer_booking.slots('demo','2026-10-25',30)
        self.assertTrue(slots)
        self.assertTrue(any('T04:00:' in slot for slot in slots))
        self.assertFalse(any('T03:' in slot for slot in slots))

    def test_malformed_write_receipt_stays_uncertain_and_reconciles_without_replay(self):
        self.queue();self.malformed_after_write=True;self.app.state.customer_booking.worker()
        self.assertEqual(self.posts,1)
        self.assertEqual(self.store.list('appointments','demo')[0]['status'],'uncertain_external')
        self.now+=timedelta(seconds=61);self.app.state.customer_booking.worker()
        self.assertEqual(self.posts,1)
        self.assertEqual(self.store.list('appointments','demo')[0]['status'],'confirmed')
