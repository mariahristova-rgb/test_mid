"""Synthetic self-service API slice on native PostgreSQL; never live OAuth."""
import json, os, subprocess, tempfile, unittest
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from threading import Thread
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from semantic_os.backend.tests import test_postgres_store as pg
from semantic_os.backend.tests.support.fault_recorder import Recorder, transport
from semantic_os.backend.assistant.connector_adapters import OfflineProviderHTTP, required_scopes
from semantic_os.backend.assistant.domain import AssistantConfig, DomainError
from semantic_os.backend.assistant.store import uid

ROOT = Path(__file__).resolve().parents[3]


@unittest.skipUnless(os.getenv('PHASE26D_PG_DISPOSABLE') == 'true', 'BLOCKED_ENVIRONMENT: disposable PG required')
class SyntheticJourneyTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {'ASSISTANT_UI_ORIGIN':'http://127.0.0.1:8021',
            'WIDGET_PUBLIC_ORIGIN':'http://127.0.0.1:8022', 'WIDGET_DEMO_SITE_ORIGINS':'http://127.0.0.1:8023'})
        environment.start(); self.addCleanup(environment.stop)
        self.fixture = pg.PostgresBookingRuntimeTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.fixture.client.close()
        self.fixture.client = TestClient(self.fixture.app, raise_server_exceptions=False)
        self.addCleanup(self.fixture.tearDown)
        self.temp = tempfile.TemporaryDirectory(prefix='phase26e-synthetic-')
        self.addCleanup(self.temp.cleanup)
        self.recorder = Recorder(Path(self.temp.name) / 'provider.sqlite')
        self.addCleanup(self.recorder.close)
        proxy = transport(self.recorder.url)
        self.worker_observing=False
        self.worker_network=[]
        def fake_provider(request):
            if self.worker_observing:
                import psycopg
                connection=getattr(self.fixture.store.transaction_state,'connection',None)
                held=False
                if connection is not None:
                    with psycopg.connect(self.fixture.dsn) as oracle:
                        held=oracle.execute("SELECT EXISTS(SELECT 1 FROM pg_locks WHERE pid=%s AND locktype='advisory' AND objid=26260001 AND granted)",(connection.info.backend_pid,)).fetchone()[0]
                self.worker_network.append({'method':request.method,'path_kind':'create' if request.method=='POST' and request.url.path.endswith('/events') else 'ownership_or_read',
                    'inside_transaction':connection is not None,'global_advisory_lock_held':held})
            if request.url.host == 'oauth2.googleapis.com':
                return httpx.Response(200, json={'access_token':'synthetic-access', 'refresh_token':'synthetic-refresh',
                    'scope':' '.join(required_scopes('google', ['availability','create'])), 'expires_in':3600})
            return proxy.handle_request(request)
        self.fixture.app.state.customer_oauth.http = OfflineProviderHTTP(httpx.MockTransport(fake_provider))
        self.rows = []

    def call(self, method, path, data=None, status=200):
        response = self.fixture.client.request(method, path, headers=self.headers, json=data)
        self.assertEqual(response.status_code, status, (path, response.status_code, response.text[:300]))
        return response.json()

    def test_complete_bilingual_api_journey(self):
        import psycopg
        store, app = self.fixture.store, self.fixture.app
        untouched = {t:store.list(t,'other') for t in ('appointments','jobs','billing_usage','audit_events')}
        for index, locale in enumerate(('bg-BG','en-US')):
            self.headers = dict(self.fixture.headers)
            registered = self.call('POST','/api/saas/register', {'name':'Synthetic Journey '+locale,
                'email':'owner@example.invalid','default_locale':locale,'timezone':'Europe/Sofia',
                'plan_id':'sandbox','event_id':uid()},201)
            tenant = registered['tenant_id']; self.headers['X-Tenant-ID'] = tenant
            token = self.call('GET','/api/saas/onboarding/mock-email')['token']
            self.call('POST','/api/saas/onboarding/verify',{'token':token})
            trial = {'plan_id':'sandbox','event_id':uid(),'confirmed':True}
            self.call('POST','/api/billing/trial',trial)
            self.call('POST','/api/billing/trial',trial)
            actor = store.principal('demo-admin',tenant)
            config = AssistantConfig(name='Synthetic '+locale, instructions='Use only approved synthetic business information.', enabled_channels=['web_chat'],
                allowed_tools=['CheckAvailability','CreateAppointment','EscalateToHuman'],
                faq_entries=[{'question_bg':'Какво предлагате?','answer_bg':'Предлагаме тестова консултация.',
                    'question_en':'What do you offer?','answer_en':'We offer a synthetic consultation.'}]).model_dump(mode='json')
            draft = self.call('POST','/api/ux/drafts',{'assistant_id':'default','config':config,
                'business':{'name':'Synthetic Journey '+locale,'timezone':'Europe/Sofia'}},201)
            resumed = self.call('GET','/api/ux/drafts')
            self.assertTrue(any(d['id']==draft['id'] and d['revision']==draft['revision'] for d in resumed))
            for language in ('bg-BG','en-US'):
                for scenario in ('booking','rejection','ambiguous','faq'):
                    result = self.call('POST',f"/api/ux/drafts/{draft['id']}/tests",{'revision':draft['revision'],'locale':language,'scenario':scenario})
                    self.assertEqual(result['verdict'],'PASS',(language,scenario))
            self.assertEqual(store.count('appointments',tenant),0)
            self.call('POST',f"/api/ux/drafts/{draft['id']}/publish",{'revision':draft['revision'],'confirmed':True})
            connection = self.call('POST','/api/customer-connectors/connections',{'provider':'google','actions':['availability','create'],'revision':1})
            self.headers['X-Tenant-ID']='other'
            denial=self.call('GET',f"/api/customer-connectors/connections/{connection['id']}/resources",status=401)
            self.assertEqual(denial['code'],'unauthorized')
            self.headers['X-Tenant-ID']=tenant
            # Explicit synthetic boundary: fake token exchange/identity, never browser consent.
            service = app.state.customer_oauth
            started = service.start(actor,connection['id'],connection['revision'])
            connected = service.complete(actor,connection['id'],'google',started['state'],started['binding'],'synthetic-code')
            self.call('GET',f"/api/customer-connectors/connections/{connection['id']}/resources")
            selected = self.call('PUT',f"/api/customer-connectors/connections/{connection['id']}/resources",{'revision':connected['revision'],'resource_ids':['calendar-owner']})
            self.call('POST',f"/api/customer-connectors/connections/{connection['id']}/booking/enable",{'revision':selected['revision'],'confirmed':False},403)
            self.call('POST',f"/api/customer-connectors/connections/{connection['id']}/booking/enable",{'revision':selected['revision'],'confirmed':True})
            conversation = self.call('POST','/api/conversations',{},201)['id']
            texts = [('Искам да запиша час за утре в 15:00.','Казвам се Иван Иванов.','Да, потвърждавам.'),
                ('Book an appointment tomorrow at 16:00.','My name is John Smith.','Yes, confirm.')][index]
            before = self.recorder.counts()['create_posts']
            for number,text in enumerate(texts):
                payload={'content':text,'event_id':f'journey-{number}','locale':locale}
                result=self.call('POST',f'/api/conversations/{conversation}/messages',payload)
                if number < 2:self.assertEqual(self.recorder.counts()['create_posts'],before)
            ledger_before=store.list('billing_usage',tenant)
            self.call('POST',f'/api/conversations/{conversation}/messages',payload)
            self.assertEqual(store.list('billing_usage',tenant),ledger_before)
            observed_before=len(self.worker_network);self.worker_observing=True
            try:app.state.customer_booking.worker();app.state.customer_booking.worker()
            finally:self.worker_observing=False
            self.assertEqual(self.recorder.counts()['create_posts'],before+1)
            appointment=store.list('appointments',tenant)[0]
            self.assertEqual(appointment['status'],'confirmed')
            self.assertEqual(appointment['locale'],locale)
            # Real domain-file HTTP proof on an allowlisted synthetic loopback origin.
            contents={}
            class Handler(BaseHTTPRequestHandler):
                def log_message(self,*args):pass
                def do_GET(self):
                    value=contents.get(self.path)
                    self.send_response(200 if value else 404)
                    self.send_header('Content-Type','text/plain');self.end_headers()
                    self.wfile.write((value or '').encode())
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            thread=Thread(target=server.serve_forever,daemon=True);thread.start()
            site='http://127.0.0.1:'+str(server.server_address[1])
            widget=app.state.widget;widget.local_sites=tuple(set(widget.local_sites)|{site})
            try:
                integration=self.call('POST','/api/widgets',{'assistant_id':'default','origins':[site],
                    'greetings':{'bg-BG':'Тестов чат.','en-US':'Synthetic chat.'},
                    'privacy_notices':{'bg-BG':'Само тестови данни.','en-US':'Synthetic data only.'},'faq_approved':True},201)
                proof=self.call('POST',f"/api/widgets/{integration['id']}/challenge",{'origin':site})
                contents[proof['path']]='deliberately-wrong-synthetic-nonce'
                self.call('POST',f"/api/widgets/{integration['id']}/verify",{'origin':site},409)
                contents[proof['path']]=proof['content']
                self.call('POST',f"/api/widgets/{integration['id']}/verify",{'origin':site})
                self.call('POST',f"/api/widgets/{integration['id']}/publish",{'draft_id':draft['id'],'confirmed':True})
                installed=self.call('GET',f"/api/widgets/{integration['id']}/installation")
                self.assertTrue(installed)
                self.call('GET','/api/usage');self.call('GET','/api/billing')
                history=self.fixture.client.get('/api/workspace/usage?period=2026-10',headers=self.headers)
            finally:server.shutdown();server.server_close();thread.join(timeout=3)
            fresh=next(row for row in self.call('GET','/api/customer-connectors/connections') if row['id']==connection['id'])
            if fresh['revision'] != selected['revision']:
                self.call('POST',f"/api/customer-connectors/connections/{connection['id']}/disconnect",{'revision':selected['revision']},409)
            self.call('POST',f"/api/customer-connectors/connections/{connection['id']}/disconnect",{'revision':fresh['revision']})
            with self.assertRaises(DomainError):app.state.customer_booking.context(tenant,write=True)
            with psycopg.connect(self.fixture.dsn,options='-c search_path='+self.fixture.schema) as db:
                confirmed=db.execute("SELECT count(*) FROM appointments WHERE tenant_id=%s AND data::jsonb->>'status'='confirmed'",(tenant,)).fetchone()[0]
                ledger=db.execute('SELECT count(*) FROM billing_usage WHERE tenant_id=%s',(tenant,)).fetchone()[0]
                sqlstate=None
                try:
                    import ast, inspect, textwrap
                    from semantic_os.backend.assistant.customer_workspace import CustomerWorkspace
                    from semantic_os.backend.assistant.postgres_store import postgres_sql
                    source=ast.parse(textwrap.dedent(inspect.getsource(CustomerWorkspace.usage)))
                    query=next(n.value for n in ast.walk(source) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.startswith('SELECT strftime'))
                    with db.transaction():
                        db.execute(postgres_sql(query),(tenant,'2026-10'))
                except psycopg.ProgrammingError as error:sqlstate=error.sqlstate
            self.assertEqual(confirmed,1)
            self.rows.append({'locale':locale,'tenant_ref':sha256(tenant.encode()).hexdigest()[:16],
                'confirmed_sql_rows':confirmed,'ledger_sql_rows':ledger,'provider_create_delta':1,
                'preview_cases':8,'status':'PASS_LOCAL_ONLY' if history.status_code==200 else 'FAIL',
                'usage_history_status':history.status_code,'independent_sqlstate':sqlstate,
                'worker_network':self.worker_network[observed_before:],
                'transport':'TestClient actual FastAPI + native PostgreSQL; independent loopback provider/domain HTTP',
                'support_interventions':['fake OAuth exchange/identity, not real consent','install synthetic nonce file'],
                'browser_completion':'NOT_TESTED'})
        for table,rows in untouched.items():self.assertEqual(store.list(table,'other'),rows)
        path=ROOT/'artifacts/phase26e/synthetic-api-journey.json';path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({'commit_sha':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'timestamp_utc':datetime.now(timezone.utc).isoformat(),'rows':self.rows,'provider':self.recorder.counts(),
            'external_provider':'BLOCKED_APPROVAL','human_accessibility':'BLOCKED_HUMAN'},indent=2)+'\n',encoding='utf-8')
        failures=[]
        for row in self.rows:
            if row['usage_history_status']!=200:failures.append(row['locale']+':usage_history_http_'+str(row['usage_history_status']))
            if any(call['global_advisory_lock_held'] for call in row['worker_network']):failures.append(row['locale']+':worker_network_under_global_lock')
        self.assertEqual(failures,[], 'Strict acceptance failures; do not substitute summary or POST-only checks')
