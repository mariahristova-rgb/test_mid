"""Real process/DB fault tests with a separate durable provider recorder."""
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json,os,subprocess,sys,tempfile,platform
from pathlib import Path
import unittest
from semantic_os.backend.tests import test_postgres_store as pg_fixture
from semantic_os.backend.tests.support.fault_recorder import Recorder,transport
from semantic_os.backend.assistant.connector_adapters import OfflineProviderHTTP
from semantic_os.backend.assistant.domain import DomainError
ROOT=Path(__file__).resolve().parents[3]


def invariant(snapshot):
    if snapshot['provider']['create_posts']>1 or snapshot['provider']['events']>1:raise AssertionError('Duplicate create attempt/effect')
    if snapshot['job']=='completed' and (snapshot['appointment']!='confirmed' or snapshot['provider']['events']!=1):raise AssertionError('Untruthful confirmation')
    if snapshot['other_appointments']!=0:raise AssertionError('Tenant leakage')
    return True


@unittest.skipUnless(os.getenv('PHASE26D_PG_DISPOSABLE')=='true','BLOCKED_ENVIRONMENT: explicit Phase26D PostgreSQL required')
class ProcessFaultTests(unittest.TestCase):
    def setUp(self):
        self.fixture=pg_fixture.PostgresBookingRuntimeTests('test_bulgarian_two_agent_confirmation_queue_and_provider_booking')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups);self.addCleanup(self.fixture.tearDown)
        self.temp=tempfile.TemporaryDirectory(prefix='phase26d-synthetic-');self.addCleanup(self.temp.cleanup)
        self.recorder=Recorder(Path(self.temp.name)/'provider.sqlite3');self.addCleanup(self.recorder.close)
        self.fixture.app.state.customer_oauth.http=OfflineProviderHTTP(transport(self.recorder.url))
        self.children=[];self.addCleanup(self.stop_children)
    def stop_children(self):
        for child in self.children:
            if child.poll() is None:child.kill();child.wait(timeout=10)
    def child(self,fault='normal',advance=0):
        service=self.fixture.app.state.customer_oauth
        data={'dsn':self.fixture.dsn,'schema':self.fixture.schema,'key':self.fixture.key,'recorder':self.recorder.url,
            'clock':(self.fixture.now+timedelta(seconds=advance)).isoformat(),'connection':self.fixture.connection['id'],
            'applications':[a.model_dump() for a in service.apps.values()],'fault':fault}
        path=Path(self.temp.name)/(str(len(self.children))+'.json');path.write_text(json.dumps(data),encoding='utf-8')
        child=subprocess.Popen([sys.executable,str(ROOT/'scripts/phase26d_fault_worker.py'),str(path)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.children.append(child);return child
    def finish(self,child,expected=0):
        out,err=child.communicate(timeout=40)
        self.assertEqual(child.returncode,expected,err.decode(errors='replace')[-2000:])
    def snapshot(self):
        import psycopg
        with psycopg.connect(self.fixture.dsn,options='-c search_path='+self.fixture.schema) as db:
            job=db.execute("SELECT data::jsonb->>'status' FROM jobs WHERE tenant_id='demo' AND data::jsonb->>'kind'='customer_calendar_create'").fetchone()
            appointment=db.execute("SELECT data::jsonb->>'status' FROM appointments WHERE tenant_id='demo'").fetchone()
            other=db.execute("SELECT count(*) FROM appointments WHERE tenant_id='other'").fetchone()[0]
            audits=db.execute("SELECT count(*) FROM audit_events WHERE tenant_id='demo'").fetchone()[0]
        return {'job':job[0] if job else None,'appointment':appointment[0] if appointment else None,'other_appointments':other,'audit_count':audits,'provider':self.recorder.counts()}
    def receipt(self,fault,before,after,**extra):
        path=ROOT/'artifacts/phase26d'/('fault-'+self._testMethodName+'.json');path.parent.mkdir(parents=True,exist_ok=True)
        sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        value={'test_id':self._testMethodName,'commit_sha':sha,'timestamp_utc':datetime.now(timezone.utc).isoformat(),
            'env':platform.platform()+' / PostgreSQL17 + independent loopback recorder','actor_reference':'synthetic_admin','approval_reference':'LOCAL_FIXTURE_ONLY',
            'fault_point':fault,'before_state':before,'observed_effect':after['provider'],'after_state':after,
            'oracle':['independent psycopg SQL','durable provider SQLite/request recorder','OS subprocess exit'],
            'result':'PASS_LOCAL_RUNTIME','artifact_path':str(path.relative_to(ROOT)),**extra}
        path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    def test_kill_before_lease_then_normal_worker(self):
        self.fixture.queue();before=self.snapshot();self.finish(self.child('before_lease'),90)
        self.assertEqual(self.snapshot()['job'],'pending');self.assertEqual(self.recorder.counts()['create_posts'],0)
        self.finish(self.child());after=self.snapshot();self.assertTrue(invariant(after));self.assertEqual(after['job'],'completed')
        self.receipt('OS exit before lease',before,after,restarts=1,exit_codes=[90,0])
    def test_kill_after_committed_claim_preserves_unknown_without_post(self):
        self.fixture.queue();before=self.snapshot();self.finish(self.child('after_claim'),91)
        self.assertEqual(self.snapshot()['job'],'running');self.finish(self.child(advance=61))
        after=self.snapshot();self.assertTrue(invariant(after));self.assertEqual(after['job'],'uncertain');self.assertEqual(after['provider']['create_posts'],0)
        self.assertGreaterEqual(after['provider']['reconcile_gets'],1)
        self.receipt('OS exit after durable claim before HTTP',before,after,restarts=1,exit_codes=[91,0])
    def test_lost_success_then_two_recovering_processes(self):
        self.fixture.queue('en-US');before=self.snapshot();self.finish(self.child('after_success'),92)
        self.assertEqual(self.snapshot()['job'],'running');self.assertEqual(self.recorder.counts()['events'],1)
        children=[self.child(advance=61),self.child(advance=61)]
        for child in children:self.finish(child)
        after=self.snapshot();self.assertTrue(invariant(after));self.assertEqual(after['job'],'completed');self.assertEqual(after['provider']['create_posts'],1)
        with self.assertRaises(AssertionError):invariant({**after,'provider':{**after['provider'],'create_posts':2}})
        with self.assertRaises(AssertionError):invariant({**after,'other_appointments':1})
        self.receipt('provider durable success/reply then OS exit before DB receipt',before,after,restarts=2,exit_codes=[92,0,0],negative_controls='duplicate attempt and cross-tenant projection rejected')
    def test_timeout_after_durable_accept_uses_get_only(self):
        self.fixture.queue();before=self.snapshot();self.recorder.mode='timeout_after_accept';self.finish(self.child())
        self.assertEqual(self.snapshot()['job'],'uncertain');self.recorder.mode='normal';self.finish(self.child(advance=61))
        after=self.snapshot();self.assertTrue(invariant(after));self.assertEqual(after['job'],'completed');self.assertEqual(after['provider']['create_posts'],1)
        self.receipt('HTTP timeout after independently committed provider event',before,after,restarts=1,reply_delivered=False)
    def test_disconnect_after_availability_before_create_denies_post(self):
        self.fixture.queue();before=self.snapshot()
        service=self.fixture.app.state.customer_oauth
        def revoke():service.disconnect(self.fixture.actor,self.fixture.connection['id'],self.fixture.connection['revision'])
        self.recorder.on_availability=revoke
        self.fixture.app.state.customer_booking.worker()
        after=self.snapshot();self.assertEqual(after['provider']['create_posts'],0)
        self.assertNotEqual(after['appointment'],'confirmed')
        self.receipt('disconnect in separate HTTP thread after FreeBusy before POST',before,after)
    def test_statement_timeout_is_classified_and_rolls_back(self):
        with self.assertRaises(DomainError) as error:
            with self.fixture.store.transaction():
                self.fixture.store.transaction_state.connection.execute("SET LOCAL statement_timeout='30ms'")
                self.fixture.store.db.execute('SELECT pg_sleep(0.2)')
        self.assertEqual(error.exception.code,'provider_error');self.assertEqual(error.exception.status,503)
        self.assertEqual(self.fixture.store.tenant('demo')['id'],'demo')
