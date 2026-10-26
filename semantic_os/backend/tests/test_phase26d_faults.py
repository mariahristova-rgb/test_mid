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
    def child(self,fault='normal',advance=0,dsn=None,mode=None,tenant='demo',iterations=10):
        service=self.fixture.app.state.customer_oauth
        data={'dsn':dsn or self.fixture.dsn,'schema':self.fixture.schema,'key':self.fixture.key,'recorder':self.recorder.url,
            'clock':(self.fixture.now+timedelta(seconds=advance)).isoformat(),'connection':self.fixture.connection['id'],
            'applications':[a.model_dump() for a in service.apps.values()],'fault':fault,'mode':mode,'tenant':tenant,'iterations':iterations}
        path=Path(self.temp.name)/(str(len(self.children))+'.json');path.write_text(json.dumps(data),encoding='utf-8')
        child=subprocess.Popen([sys.executable,str(ROOT/'scripts/phase26d_fault_worker.py'),str(path)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.children.append(child);return child
    def finish(self,child,expected=0):
        out,err=child.communicate(timeout=40)
        self.assertEqual(child.returncode,expected,err.decode(errors='replace')[-2000:])
    def snapshot(self,dsn=None):
        import psycopg
        with psycopg.connect(dsn or self.fixture.dsn,options='-c search_path='+self.fixture.schema) as db:
            job=db.execute("SELECT data::jsonb->>'status',data::jsonb->>'event_id',id,data::jsonb->>'correlation_id' FROM jobs WHERE tenant_id='demo' AND data::jsonb->>'kind'='customer_calendar_create'").fetchone()
            appointment=db.execute("SELECT data::jsonb->>'status',id FROM appointments WHERE tenant_id='demo'").fetchone()
            other=db.execute("SELECT count(*) FROM appointments WHERE tenant_id='other'").fetchone()[0]
            audits=db.execute("SELECT count(*) FROM audit_events WHERE tenant_id='demo'").fetchone()[0]
            contacts=db.execute("SELECT count(*) FROM contacts WHERE tenant_id='demo'").fetchone()[0]
        value={'job':job[0] if job else None,'appointment':appointment[0] if appointment else None,'other_appointments':other,'audit_count':audits,'contact_count':contacts,'job_ref':sha256(job[2].encode()).hexdigest()[:16] if job else None,'external_ref':sha256(job[1].encode()).hexdigest()[:16] if job else None,'correlation_ref':sha256((job[3] or '').encode()).hexdigest()[:16] if job else None,'booking_ref':sha256(appointment[1].encode()).hexdigest()[:16] if appointment else None,'provider':self.recorder.counts()}
        self.last_snapshot=value
        return value
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
        before=self.snapshot()
        with self.assertRaises(DomainError) as error:
            with self.fixture.store.transaction():
                self.fixture.store.add('contacts','demo',{'name':'Synthetic rollback marker'},external_key='timeout-marker')
                self.fixture.store.transaction_state.connection.execute("SET LOCAL statement_timeout='30ms'")
                self.fixture.store.db.execute('SELECT pg_sleep(0.2)')
        self.assertEqual(error.exception.code,'provider_error');self.assertEqual(error.exception.status,503)
        self.assertIsNone(self.fixture.store.find('contacts','demo','timeout-marker'))
        after=self.snapshot();self.assertEqual(after['contact_count'],before['contact_count'])
        self.receipt('statement timeout after an uncommitted contact write',before,after,error_classification='provider_error/503')

    def test_terminated_database_transaction_rolls_back_booking_transition(self):
        import psycopg
        self.fixture.queue();before=self.snapshot()
        job=next(j for j in self.fixture.store.list('jobs','demo') if j.get('kind')=='customer_calendar_create')
        with self.assertRaises(DomainError) as error:
            with self.fixture.store.transaction():
                self.fixture.store.update('jobs','demo',job['id'],{'status':'completed'})
                self.fixture.store.update('appointments','demo',job['appointment_id'],{'status':'confirmed'})
                target=self.fixture.store.transaction_state.connection.info.backend_pid
                with psycopg.connect(self.fixture.dsn,autocommit=True) as killer:
                    self.assertTrue(killer.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid=%s AND datname='phase26c_fixture' AND application_name='ontelyx-assistant'",(target,)).fetchone()[0])
                self.fixture.store.db.execute('SELECT 1')
        self.assertEqual(error.exception.code,'provider_error')
        after=self.snapshot();self.assertEqual(after['job'],'pending');self.assertEqual(after['appointment'],'pending_external');self.assertTrue(invariant(after))
        self.receipt('pg_terminate_backend after uncommitted booking updates',before,after,error_classification=error.exception.code)

    def test_pool_exhaustion_and_global_lock_timeout_are_bounded(self):
        from semantic_os.backend.assistant.postgres_store import PostgresStore
        from threading import Event,Thread
        self.fixture.store.pool.timeout=.05
        held=[self.fixture.store.pool.getconn(),self.fixture.store.pool.getconn()]
        try:
            with self.assertRaises(DomainError) as error:self.fixture.store.db.execute('SELECT 1')
            self.assertEqual(error.exception.code,'provider_error');self.assertEqual(error.exception.status,503)
        finally:
            for connection in held:self.fixture.store.pool.putconn(connection)
        entered,release=Event(),Event()
        def hold():
            with self.fixture.store.transaction():entered.set();release.wait(3)
        thread=Thread(target=hold);thread.start();self.assertTrue(entered.wait(3))
        second=PostgresStore(self.fixture.dsn,schema=self.fixture.schema,pool_size=1)
        try:
            with second.pool.connection() as connection:connection.execute("SET lock_timeout='40ms'")
            with self.assertRaises(DomainError) as error:
                with second.transaction():pass
            self.assertEqual(error.exception.code,'provider_error')
        finally:release.set();thread.join(timeout=5);second.close()
        self.assertEqual(self.fixture.store.tenant('demo')['id'],'demo')

    def test_native_restore_to_second_instance_preserves_uncertain_intent(self):
        import psycopg,copy
        from semantic_os.backend.tests.support.restore_oracle import native_restore,assert_restored
        restore=os.environ.get('PHASE26D_RESTORE_DSN','')
        self.assertTrue(restore,'Independent restore instance required; do not substitute same DB')
        for tenant in ('demo','other'):
            self.fixture.store.add('billing_usage',tenant,{'quantity':1,'category':'synthetic','billing_period':'2026-10'},external_key='restore-idempotency')
        self.fixture.queue();before=self.snapshot();self.finish(self.child('after_success'),92)
        artifact=ROOT/'artifacts/phase26d'/('uncertain-'+self.fixture.schema+'.dump');artifact.parent.mkdir(parents=True,exist_ok=True)
        try:
            result=native_restore(self.fixture.dsn,restore,self.fixture.schema,artifact)
            (ROOT/'artifacts/phase26d/restore-content-checks.json').write_text(json.dumps({'result':'NOT_RUN','scope':'content/catalog checks complete; later enforcement controls pending','restore':result},indent=2),encoding='utf-8')
            self.assertEqual(result['actual']['catalog']['ledger_trigger'],1)
            self.assertGreater(result['actual']['catalog']['foreign_keys'],0)
            broken=copy.deepcopy(result['actual']);broken['tables']['jobs']['sha256']='0'*64
            with self.assertRaises(AssertionError):assert_restored(result['expected'],broken)
            with psycopg.connect(restore,options='-c search_path='+self.fixture.schema) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM tenants').fetchone()[0],2)
                ledger_count=db.execute("SELECT count(*) FROM billing_usage WHERE tenant_id='demo'").fetchone()[0]
                with self.assertRaises(psycopg.IntegrityError):
                    with db.transaction():db.execute("DELETE FROM billing_usage WHERE tenant_id='demo'")
                self.assertEqual(db.execute("SELECT count(*) FROM billing_usage WHERE tenant_id='demo'").fetchone()[0],ledger_count)
            self.assertEqual(self.snapshot(restore)['job'],'running')
            self.finish(self.child(advance=61,dsn=restore))
            after=self.snapshot(restore);self.assertEqual(after['job'],'completed');self.assertTrue(invariant(after))
            self.assertEqual(self.snapshot()['job'],'running')
            self.receipt('native pg_dump restored into independent PostgreSQL instance then GET-only recovery',before,after,
                restore=result,restarts=1,negative_controls='altered content hash and raw ledger DELETE rejected')
        finally:
            with psycopg.connect(restore,autocommit=True) as db:db.execute('DROP SCHEMA IF EXISTS '+self.fixture.schema+' CASCADE')

    def test_cross_tenant_global_serialization_measurement(self):
        from time import perf_counter
        for tenant in ('demo','other'):
            self.fixture.store.add('operations_events',tenant,{'kind':'synthetic_counter','value':0},external_key='phase26d-counter')
        results={}
        for label,tenants in [('same_tenant',['demo','demo']),('cross_tenant',['demo','other'])]:
            for tenant in ('demo','other'):
                row=self.fixture.store.find('operations_events',tenant,'phase26d-counter')
                self.fixture.store.update('operations_events',tenant,row['id'],{'value':0})
            start=perf_counter();children=[self.child(mode='counter',tenant=tenant) for tenant in tenants];measure=[]
            for child in children:
                out,err=child.communicate(timeout=40);self.assertEqual(child.returncode,0,err.decode(errors='replace')[-1000:]);measure.append(json.loads(out))
            interval=max(r['finished_monotonic'] for r in measure)-min(r['started_monotonic'] for r in measure)
            count=sum(self.fixture.store.find('operations_events',tenant,'phase26d-counter')['value'] for tenant in ('demo','other'))
            self.assertEqual(count,20)
            results[label]={'processes':2,'committed_operations':count,'operation_interval_seconds':round(interval,4),'process_startup_inclusive_seconds':round(perf_counter()-start,4),'operations_per_second':round(count/interval,3)}
        before=self.snapshot();self.receipt('same/cross-tenant two-process serialized writes',before,before,measurements=results,global_write_lock_retained=True,throughput_scope='synthetic operation only; no production capacity inference')

    def test_forced_deadlock_has_independent_sqlstate_and_recovers(self):
        import psycopg
        from threading import Barrier
        from concurrent.futures import ThreadPoolExecutor
        barrier=Barrier(2)
        def competing(first,second):
            with psycopg.connect(self.fixture.dsn,autocommit=True) as connection:
                connection.execute('SET search_path TO '+self.fixture.schema)
                connection.execute("SET deadlock_timeout='50ms'")
                try:
                    with connection.transaction():
                        connection.execute('SELECT 1 FROM tenants WHERE id=%s FOR UPDATE',(first,))
                        barrier.wait(timeout=3)
                        connection.execute('SELECT 1 FROM tenants WHERE id=%s FOR UPDATE',(second,))
                    return 'committed'
                except psycopg.errors.DeadlockDetected as error:return error.sqlstate
        with ThreadPoolExecutor(max_workers=2) as workers:
            futures=[workers.submit(competing,'demo','other'),workers.submit(competing,'other','demo')]
            outcomes=[future.result(timeout=5) for future in futures]
        self.assertEqual(sorted(outcomes),['40P01','committed'])
        self.assertEqual(self.fixture.store.tenant('demo')['id'],'demo')
        before=self.snapshot();self.receipt('adversarial raw SQL lock ordering in fixture only',before,before,sqlstates=outcomes,global_store_lock_bypassed_for_fault_construction=True)

    def test_disconnect_after_admission_records_real_receipt_without_replay(self):
        self.fixture.queue();before=self.snapshot()
        service=self.fixture.app.state.customer_oauth
        self.recorder.on_create=lambda:service.disconnect(self.fixture.actor,self.fixture.connection['id'],self.fixture.connection['revision'])
        self.fixture.app.state.customer_booking.worker()
        after=self.snapshot();self.assertTrue(invariant(after));self.assertEqual(after['job'],'completed')
        self.assertEqual(after['provider']['create_posts'],1)
        self.assertEqual(service.row(self.fixture.actor,self.fixture.connection['id'])['state'],'disconnected')
        with self.assertRaises(DomainError):self.fixture.app.state.customer_booking.context('demo',write=True)
        self.fixture.app.state.customer_booking.worker();self.assertEqual(self.recorder.counts()['create_posts'],1)
        self.receipt('disconnect after durable admission and accepted external effect',before,after,authorization_cutoff='committed write_admitted_at; receipt is truth, not new consent')

    def test_revoked_uncertain_write_stays_unknown_without_unauthorized_get(self):
        self.fixture.queue();before=self.snapshot();self.recorder.mode='timeout_after_accept';self.finish(self.child())
        service=self.fixture.app.state.customer_oauth
        service.disconnect(self.fixture.actor,self.fixture.connection['id'],self.fixture.connection['revision'])
        self.recorder.mode='normal';self.finish(self.child(advance=61))
        after=self.snapshot();self.assertTrue(invariant(after));self.assertEqual(after['job'],'uncertain')
        self.assertEqual(after['provider']['create_posts'],1);self.assertEqual(after['provider']['reconcile_gets'],0)
        self.receipt('revoked grant after accepted write/timeout before reconciliation',before,after,restarts=1,reauthorization_required_to_reconcile=True)

    def test_removed_resource_access_after_availability_denies_create(self):
        self.fixture.queue();before=self.snapshot()
        self.recorder.on_availability=lambda:setattr(self.recorder,'mode','access_removed')
        self.fixture.app.state.customer_booking.worker()
        after=self.snapshot();self.assertEqual(after['provider']['create_posts'],0);self.assertEqual(after['job'],'blocked')
        self.receipt('resource ownership removed after availability before final admission',before,after)
