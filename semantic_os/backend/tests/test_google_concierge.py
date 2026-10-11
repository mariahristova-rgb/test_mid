"""Offline Google contracts; never authorize or call the owner's live account."""
import json
import unittest
from datetime import datetime,timedelta,timezone,date
from urllib.parse import parse_qs,urlsplit
from cryptography.fernet import Fernet
import httpx
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.security import TenantSecretStore
from semantic_os.backend.assistant.google_workspace import GoogleWorkspace,GoogleClientConfig,SCOPES,ACCOUNT
from semantic_os.backend.assistant.concierge import Concierge,ConciergePolicy
from semantic_os.backend.assistant.orchestration import Orchestrator
from semantic_os.backend.assistant.providers import ProviderRegistry
from semantic_os.backend.assistant.domain import DomainError

class GoogleConciergeTests(unittest.TestCase):
    def setUp(self):
        self.store=Store();self.store.seed();self.store.seed('other','other')
        self.now=datetime(2026,10,12,6,tzinfo=timezone.utc);self.actor=self.store.principal('demo-admin','demo')
        self.secrets=TenantSecretStore(self.store,Fernet.generate_key().decode());self.events={};self.busy=[];self.sent=0;self.google_identity=ACCOUNT
        self.workspace=GoogleWorkspace(self.store,self.secrets,lambda:self.now,development=True,transport=httpx.MockTransport(self.transport))
        self.engine=Orchestrator(self.store,ProviderRegistry(),clock=lambda:self.now)
        self.concierge=Concierge(self.store,self.engine,self.workspace,self.secrets,public_origin='http://127.0.0.1:3020')
        self.concierge.configure(self.actor,ConciergePolicy(enabled=True,operations_authorized=True,management_origin='http://127.0.0.1:3020'))
        self.conversation=self.engine.conversation(self.actor,'default');self.conversation=self.store.update('conversations','demo',self.conversation['id'],{'widget_public_id':'wdg_test','active_locale':'bg-BG'})
        self.assistant=self.store.update('assistants','demo','default',{'allowed_tools':['ConciergeAvailability','ConciergeBooking','ConciergeManage','ConciergeRequest']})
        self.requests=[]

    def tearDown(self):self.store.close()

    def transport(self,request):
        self.requests.append(request.url.path);path=request.url.path
        if path.endswith('/token'):
            data=parse_qs(request.content.decode());kind='gmail' if 'gmail' in data.get('client_id',[''])[0] else 'calendar'
            return httpx.Response(200,json={'access_token':'offline-access','refresh_token':'offline-refresh','expires_in':3600,'scope':' '.join(SCOPES[kind])})
        if path.endswith('/userinfo'):return httpx.Response(200,json={'email':self.google_identity,'email_verified':True})
        if path.endswith('/revoke'):return httpx.Response(200,json={})
        if path.endswith('/freeBusy'):return httpx.Response(200,json={'calendars':{'primary':{'busy':[*self.busy,*[{'start':event['start']['dateTime'],'end':event['end']['dateTime']} for event in self.events.values() if event['status']=='confirmed']]}}})
        if '/calendarList/' in path:return httpx.Response(200,json={'id':ACCOUNT,'accessRole':'owner','conferenceProperties':{'allowedConferenceSolutionTypes':['hangoutsMeet']}})
        if path.endswith('/messages/send'):
            self.sent+=1;return httpx.Response(200,json={'id':'mail-'+str(self.sent)})
        if path.endswith('/events') and request.method=='POST':
            body=json.loads(request.content)
            if body['id'] in self.events:return httpx.Response(409,json={})
            self.events[body['id']]={**body,'status':'confirmed','etag':'"one"'};return httpx.Response(200,json=self.events[body['id']])
        if path.endswith('/events') and request.method=='GET':return httpx.Response(200,json={'items':list(self.events.values())})
        identity=path.rsplit('/',1)[-1]
        if identity in self.events:
            if request.method=='GET':return httpx.Response(200,json=self.events[identity])
            if request.method=='DELETE':self.events[identity]['status']='cancelled';return httpx.Response(204)
            if request.method=='PATCH':self.events[identity].update(json.loads(request.content));self.events[identity]['etag']='"two"';return httpx.Response(200,json=self.events[identity])
        return httpx.Response(404,json={})

    def connect(self,kind='calendar'):
        self.workspace.configure(self.actor,GoogleClientConfig(kind=kind,client_id=kind+'-fixture.apps.googleusercontent.com',client_secret='fake',redirect_uri='http://127.0.0.1:3017/backend/api/google/oauth/callback'))
        url,binding=self.workspace.start(self.actor,kind);query=parse_qs(urlsplit(url).query)
        self.assertIn('code_challenge',query)
        self.workspace.callback(query['state'][0],'offline-code',{kind:binding})

    def verified_email(self):
        self.connect('gmail');result=self.concierge.verify_email(self.actor,self.conversation,'visitor@example.com')
        jobs=self.store.list('jobs','demo');body=self.secrets.get('demo','concierge:mail:'+jobs[-1]['id']);code=body.rsplit(' ',1)[-1]
        self.concierge.confirm_email(self.actor,self.conversation,result['verification_id'],code)
        return result['verification_id']

    def book(self,key='one'):
        self.connect();verification=self.verified_email()
        args={'starts_at':'2026-10-12T15:00:00+03:00','name':'Fictional visitor','email':'visitor@example.com','topic':'Demo','company':'Example','verification_id':verification,'consent':True}
        result=self.engine.tools.execute(
            self.actor,self.assistant,self.conversation,'ConciergeBooking',args,
            key=key,
            correlation_id='offline',
            approved=True,
        )
        return result,args

    def test_oauth_binding_account_replay_and_encryption(self):
        cfg=GoogleClientConfig(kind='calendar',client_id='calendar-fixture.apps.googleusercontent.com',client_secret='fake',redirect_uri='http://127.0.0.1:3017/backend/api/google/oauth/callback')
        self.workspace.configure(self.actor,cfg);url,binding=self.workspace.start(self.actor,'calendar');state=parse_qs(urlsplit(url).query)['state'][0]
        with self.assertRaises(DomainError):self.workspace.callback(state,'code',{'calendar':'wrong-browser'})
        self.workspace.callback(state,'code',{'calendar':binding})
        with self.assertRaises(DomainError):self.workspace.callback(state,'code',{'calendar':binding})
        self.assertNotIn('offline-refresh',json.dumps(self.store.list('secrets','demo')))
        self.assertNotIn('offline-access',json.dumps(self.workspace.status(self.actor)))
        self.assertEqual(self.workspace.row('demo','calendar')['account'],ACCOUNT)

    def test_wrong_google_account_is_rejected(self):
        self.google_identity='someone@example.com'
        with self.assertRaises(DomainError):self.connect()
        self.assertNotEqual(self.workspace.row('demo','calendar')['state'],'connected')

    def test_live_operations_blocked_without_owner_permission(self):
        self.connect();self.connect('gmail');policy=self.concierge.policy('demo');policy.operations_authorized=False;self.concierge.configure(self.actor,policy)
        with self.assertRaises(DomainError):self.concierge.ready('demo',True)
        self.assertFalse(self.events);self.assertEqual(self.sent,0)

    def test_live_freebusy_cutoff_buffers_and_timezone(self):
        self.connect();self.busy=[{'start':'2026-10-12T12:00:00Z','end':'2026-10-12T12:30:00Z'}]
        slots=self.concierge.slots('demo',date(2026,10,12))['slots']
        self.assertNotIn('2026-10-12T14:45:00+03:00',slots);self.assertIn('2026-10-12T15:45:00+03:00',slots)
        self.assertTrue(all(datetime.fromisoformat(slot).hour<19 for slot in slots))
        for day in (date(2026,10,11),date(2027,1,4)):
            with self.assertRaises(DomainError):self.concierge.slots('demo',day)
        self.assertTrue(all(slot.endswith('+02:00') for slot in self.concierge.slots('demo',date(2026,11,2))['slots']))

    def test_confirmation_single_event_and_persisted_booking(self):
        result,args=self.book();repeated=self.engine.tools.execute(self.actor,self.assistant,self.conversation,'ConciergeBooking',args,key='one',correlation_id='offline',approved=True)
        self.assertEqual(result,repeated);self.assertEqual(len(self.events),1);self.assertEqual(self.store.count('appointments','demo'),1);self.assertEqual(self.store.count('appointments','other'),0)
        with self.assertRaises(DomainError):self.engine.tools.execute(self.actor,self.assistant,self.conversation,'ConciergeBooking',args,key='not-confirmed',correlation_id='offline')

    def test_email_proof_and_owned_management(self):
        result,_=self.book();booking=self.store.get('operations_events','demo',result['data']['booking_id']);token=self.concierge.management_token('demo',booking)
        with self.assertRaises(DomainError):self.concierge.owned('other',token)
        with self.assertRaises(DomainError):self.concierge.owned('demo',token[:-1]+'x')
        changed=self.concierge.manage(self.actor,self.conversation,{'action':'reschedule','management_token':token,'starts_at':'2026-10-13T16:00:00+03:00','consent':True})
        self.assertEqual(changed['status'],'confirmed')
        with self.assertRaises(DomainError):self.concierge.owned('demo',token)
        updated=self.store.get('operations_events','demo',booking['id']);newtoken=self.concierge.management_token('demo',updated)
        cancelled=self.concierge.manage(self.actor,self.conversation,{'action':'cancel','management_token':newtoken,'consent':True});self.assertEqual(cancelled['status'],'cancelled')
        self.assertFalse(any(job['status']=='pending' and job.get('booking_id')==booking['id'] for job in self.store.list('jobs','demo')))

    def test_reminder_runs_once_and_never_after_start(self):
        result,_=self.book();self.concierge.worker();count=self.sent;self.concierge.worker();self.assertEqual(self.sent,count)
        self.now=datetime(2026,10,12,14,tzinfo=timezone.utc);self.concierge.worker()
        self.assertEqual(self.sent,count)

    def test_requests_persist_without_marketing_subscription(self):
        args={'action':'feature','name':'','email':'','company':'','topic':'Feature proposal','timeline':'','impact':'Useful','verification_id':'','consent':True,'marketing_consent':False}
        result=self.concierge.request(self.actor,self.conversation,args,'feature-one')
        self.assertEqual(result['status'],'received');self.assertFalse(self.concierge.rows('demo','concierge_request')[0]['marketing_consent'])

    def test_another_action_cannot_double_book_a_google_slot(self):
        _,args=self.book()
        with self.assertRaises(DomainError):self.engine.tools.execute(self.actor,self.assistant,self.conversation,'ConciergeBooking',args,key='different-action',correlation_id='offline',approved=True)
        self.assertEqual(len(self.events),1)

    def test_verified_recovery_does_not_return_a_management_capability(self):
        result,_=self.book();booking=self.store.get('operations_events','demo',result['data']['booking_id'])
        verifier=self.verified_email();outcome=self.concierge.recover_management(self.actor,self.conversation,booking['id'],'visitor@example.com',verifier)
        self.assertEqual(outcome,{'status':'queued'});self.assertNotIn('token',outcome)

    def test_future_booking_year_can_be_configured(self):
        self.connect();policy=self.concierge.policy('demo');policy.ends_on=date(2027,12,31);self.concierge.configure(self.actor,policy)
        self.assertTrue(self.concierge.slots('demo',date(2027,1,4))['slots'])

    def test_refresh_revocation_and_expired_ownership(self):
        self.connect();self.now+=timedelta(hours=2);self.assertEqual(self.workspace.token('demo','calendar'),'offline-access')
        self.workspace.revoke(self.actor,'calendar')
        with self.assertRaises(DomainError):self.workspace.token('demo','calendar')
        result,_=self.book();booking=self.store.get('operations_events','demo',result['data']['booking_id']);token=self.concierge.management_token('demo',booking)
        self.now+=timedelta(days=8)
        with self.assertRaises(DomainError):self.concierge.owned('demo',token)

    def test_uncertain_gmail_send_is_never_replayed(self):
        self.connect('gmail')
        self.concierge.queue_email('demo',self.conversation['id'],'visitor@example.com','Approved test','Public information','uncertain')
        original=self.workspace.transport
        def uncertain(request):
            if request.url.path.endswith('/messages/send'):
                self.sent+=1;raise httpx.ReadTimeout('offline timeout',request=request)
            return self.transport(request)
        self.workspace.transport=httpx.MockTransport(uncertain)
        self.concierge.worker();self.concierge.worker()
        self.assertEqual(self.sent,1);self.assertEqual(self.store.list('jobs','demo')[0]['status'],'delivery_unknown')
        self.workspace.transport=original

    def test_request_retention_redacts_copies_and_cancels_stale_notification(self):
        policy=self.concierge.policy('demo');policy.request_retention_days=1;self.concierge.configure(self.actor,policy)
        args={'action':'feature','name':'Fictional contact','email':'','company':'Example','topic':'Private visitor proposal','impact':'Useful feature','consent':True}
        outcome=self.engine.tools.execute(self.actor,self.assistant,self.conversation,'ConciergeRequest',args,key='retention',correlation_id='retention',approved=True)
        self.now+=timedelta(days=2);self.assertEqual(self.concierge.purge_requests(),1)
        row=self.store.get('operations_events','demo',outcome['data']['request_id']);self.assertTrue(row['redacted']);self.assertEqual(row['topic'],'')
        self.assertEqual(self.store.list('tool_executions','demo')[-1]['arguments'],{'redacted':True})
        self.assertEqual(self.store.list('jobs','demo')[-1]['status'],'cancelled')
