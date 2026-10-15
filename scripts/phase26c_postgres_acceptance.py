"""Real local PostgreSQL acceptance and synthetic contention; never customer data."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import statistics
import sys
from time import perf_counter
import unittest
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def run():
    import psycopg
    from semantic_os.backend.assistant.postgres_store import PostgresStore
    dsn=os.environ.get('PHASE26C_PG_DSN','')
    info=psycopg.conninfo.conninfo_to_dict(dsn)
    if os.getenv('PHASE26C_PG_DISPOSABLE')!='true' or info.get('host')!='127.0.0.1' or info.get('port')!='55426' or info.get('dbname')!='phase26c_fixture':
        return {'scope':'LOCAL_POSTGRES_RUNTIME','status':'BLOCKED','reason':'explicit_loopback_fixture_required'}
    suite=unittest.defaultTestLoader.loadTestsFromName('semantic_os.backend.tests.test_postgres_store')
    started=perf_counter();result=unittest.TextTestRunner(verbosity=1).run(suite)
    report={'scope':'LOCAL_POSTGRES_RUNTIME','status':'PASS_LOCAL_RUNTIME' if result.wasSuccessful() and not result.skipped else 'FAIL',
        'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'test_seconds':round(perf_counter()-started,3),
        'production_ready':False,'distributed_scaling_accepted':False}
    if not result.wasSuccessful(): return report
    schema='measure_'+uuid4().hex
    with psycopg.connect(dsn,autocommit=True) as conn: conn.execute('CREATE SCHEMA '+schema)
    stores=[]
    try:
        stores=[PostgresStore(dsn,schema=schema,pool_size=2,migrate=True),PostgresStore(dsn,schema=schema,pool_size=2)]
        stores[0].seed('synthetic','synthetic-admin')
        counter=stores[0].add('operations_events','synthetic',{'kind':'synthetic_counter','count':0})
        latency=[]
        for _ in range(100):
            start=perf_counter();stores[0].tenant('synthetic');latency.append((perf_counter()-start)*1000)
        def writes(store):
            samples=[]
            for _ in range(25):
                start=perf_counter()
                with store.transaction():
                    row=store.get('operations_events','synthetic',counter['id'])
                    store.update('operations_events','synthetic',counter['id'],{'count':row['count']+1})
                samples.append((perf_counter()-start)*1000)
            return samples
        with ThreadPoolExecutor(max_workers=2) as workers:
            contention=sum(list(workers.map(writes,stores)),[])
        def distribution(values):
            return {'samples':len(values),'p50_ms':round(statistics.median(values),3),'p95_ms':round(sorted(values)[int(.95*(len(values)-1))],3)}
        report.update(read_latency=distribution(latency),two_worker_transaction_latency=distribution(contention),
            expected_increments=50,actual_increments=stores[0].get('operations_events','synthetic',counter['id'])['count'],
            pools=[store.pool.get_stats() for store in stores])
        if report['actual_increments']!=50:report['status']='FAIL'
        return report
    finally:
        for store in stores:store.close()
        with psycopg.connect(dsn,autocommit=True) as conn:conn.execute('DROP SCHEMA '+schema+' CASCADE')


if __name__=='__main__':
    report=run();target=ROOT/'artifacts/phase26c/postgres-runtime.json';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))
    raise SystemExit(0 if report['status']=='PASS_LOCAL_RUNTIME' else 1)
