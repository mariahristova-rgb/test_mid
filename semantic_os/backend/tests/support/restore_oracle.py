"""Native PostgreSQL independent catalog/hash/restore oracle; fixture only."""
from hashlib import sha256
import json,os,re,subprocess
from time import perf_counter
from pathlib import Path

def catalog(connection,schema):
    # Canonical qualification must not depend on each client search_path.
    connection.execute("SET LOCAL search_path=pg_catalog")
    return {'foreign_keys':connection.execute("SELECT count(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname=%s AND contype='f' AND convalidated",(schema,)).fetchone()[0],
        'check_constraints':connection.execute("SELECT count(*) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname=%s AND contype='c' AND convalidated",(schema,)).fetchone()[0],
        'indexes':connection.execute('SELECT count(*) FROM pg_indexes WHERE schemaname=%s',(schema,)).fetchone()[0],
        'foreign_key_definitions':[sha256(row[0].encode()).hexdigest() for row in connection.execute("SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname=%s AND contype='f' ORDER BY c.conname",(schema,))],
        'index_definitions':[sha256(row[0].encode()).hexdigest() for row in connection.execute('SELECT indexdef FROM pg_indexes WHERE schemaname=%s ORDER BY indexname',(schema,))],
        'trigger_definitions':[sha256(row[0].encode()).hexdigest() for row in connection.execute("SELECT pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND NOT t.tgisinternal ORDER BY t.tgname",(schema,))],
        'ledger_trigger':connection.execute("SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND t.tgname='billing_usage_append_only' AND t.tgenabled='O'",(schema,)).fetchone()[0]}

def projections(connection,schema):
    from psycopg import sql
    names=[r[0] for r in connection.execute("SELECT tablename FROM pg_tables WHERE schemaname=%s ORDER BY tablename",(schema,))]
    result={}
    for name in names:
        rows=[r[0] for r in connection.execute(sql.SQL('SELECT row_to_json(t) FROM {}.{} t').format(sql.Identifier(schema),sql.Identifier(name)))]
        values=[]
        for row in rows:
            if isinstance(row.get('data'),str):row['data']=json.loads(row['data'])
            values.append(row)
        payload=json.dumps(sorted(values,key=lambda row:json.dumps(row,sort_keys=True)),sort_keys=True,ensure_ascii=False).encode()
        result[name]={'rows':len(rows),'sha256':sha256(payload).hexdigest()}
    return result

def assert_restored(expected,actual):
    if expected!=actual:raise AssertionError('Restore projection/catalog mismatch')

def native_restore(dsn,restore_dsn,schema,artifact):
    import psycopg
    source=os.environ.get('PHASE26D_SOURCE_CONTAINER','');target=os.environ.get('PHASE26D_RESTORE_CONTAINER','')
    if not source or not target or source==target or not re.fullmatch('fixture_[0-9a-f]{32}',schema):raise RuntimeError('Two explicit fixture containers required')
    def docker(*args,input=None):return subprocess.run(['docker',*args],input=input,capture_output=True,check=True,timeout=60).stdout
    for container,port in [(source,'55426'),(target,'55427')]:
        meta=json.loads(docker('inspect',container))[0]
        ports=meta['HostConfig']['PortBindings'].get('5432/tcp',[])
        if not any(p['HostPort']==port for p in ports):raise RuntimeError('Fixture binding mismatch')
        if not os.getenv('CI') and (meta['Config']['Labels'].get('purpose')!='test-mid-phase26d' or any(p.get('HostIp')!='127.0.0.1' for p in ports)):
            raise RuntimeError('Owned isolated fixtures required')
    with psycopg.connect(dsn,autocommit=True) as connection:
        connection.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        expected={'tables':projections(connection,schema),'catalog':catalog(connection,schema)}
        snapshot=connection.execute('SELECT pg_export_snapshot()').fetchone()[0]
        dump_started=perf_counter()
        dump=docker('exec',source,'pg_dump','-U','postgres','-d','phase26c_fixture','--schema',schema,'--snapshot',snapshot,'-Fc')
        dump_seconds=perf_counter()-dump_started
        connection.execute('COMMIT')
    artifact=Path(artifact);artifact.write_bytes(dump)
    listing=docker('exec','-i',target,'pg_restore','--list',input=dump)
    with psycopg.connect(restore_dsn,autocommit=True) as connection:
        if connection.execute('SELECT 1 FROM pg_namespace WHERE nspname=%s',(schema,)).fetchone():raise RuntimeError('Restore target schema must be new')
    started=perf_counter()
    docker('exec','-i',target,'pg_restore','--exit-on-error','-U','postgres','-d','phase26c_fixture',input=dump)
    with psycopg.connect(restore_dsn,options='-c search_path='+schema) as connection:
        actual={'tables':projections(connection,schema),'catalog':catalog(connection,schema)}
        assert_restored(expected,actual)
        version=connection.execute('SHOW server_version').fetchone()[0]
    return {'expected':expected,'actual':actual,'dump_sha256':sha256(dump).hexdigest(),'dump_bytes':len(dump),
        'pg_restore_list_entries':len([line for line in listing.splitlines() if line and not line.startswith(b';')]),
        'dump_seconds':round(dump_seconds,3),'database_restore_validation_seconds':round(perf_counter()-started,3),
        'snapshot_acknowledged_records_lost':0,'pg_verifybackup':'NOT_APPLICABLE_LOGICAL_DUMP','postgres_version':version}
