"""Native runtime migration/pg_dump restore on a labelled disposable container only."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def run():
    import psycopg
    from semantic_os.backend.assistant.store import Store,TABLES
    from semantic_os.backend.assistant.postgres_store import PostgresStore
    dsn=os.environ.get('PHASE26C_PG_DSN','')
    info=psycopg.conninfo.conninfo_to_dict(dsn)
    if os.getenv('PHASE26C_PG_DISPOSABLE')!='true' or info.get('host')!='127.0.0.1' or info.get('port')!='55426' or info.get('dbname')!='phase26c_fixture':
        raise RuntimeError('Disposable loopback fixture required')
    def docker(*args,input=None):
        return subprocess.run(['docker',*args],input=input,capture_output=True,check=True,timeout=60).stdout
    meta=json.loads(docker('inspect','test-mid-phase26c-pg'))[0]
    if meta['Config']['Labels'].get('purpose')!='test-mid-phase26c' or meta['HostConfig']['PortBindings']!={'5432/tcp':[{'HostIp':'127.0.0.1','HostPort':'55426'}]}:
        raise RuntimeError('Fixture container identity mismatch')
    schema='migration_'+uuid4().hex
    restore='restore_'+uuid4().hex
    source=Store();target=None;restored=None
    try:
        source.seed('synthetic-a','synthetic-admin-a');source.seed('synthetic-b','synthetic-admin-b')
        for tenant,name in [('synthetic-a','Синтетичен клиент'),('synthetic-b',"Synthetic O'Brien")]:
            conversation=source.add('conversations',tenant,{'assistant_id':'default','channel':'web_chat'})
            appointment=source.add('appointments',tenant,{'assistant_id':'default','conversation_id':conversation['id'],'name':name,'status':'uncertain_external','starts_at':'2026-10-15T15:00:00+03:00'})
            source.add('jobs',tenant,{'kind':'customer_calendar_create','status':'uncertain','appointment_id':appointment['id'],'event_id':'synthetic-event'})
            source.add('billing_usage',tenant,{'quantity':1,'category':'synthetic','billing_period':'2026-10'})
        with psycopg.connect(dsn,autocommit=True) as conn:conn.execute('CREATE SCHEMA '+schema)
        target=PostgresStore(dsn,schema=schema,migrate=True,pool_size=2)
        tables=['tenants',*TABLES,'saas_plans','platform_audit']
        # New target only; deferred tenant FKs preserve atomic all-table import.
        with target.transaction():
            conn=target.transaction_state.connection
            for table in TABLES:
                for constraint in conn.execute("SELECT conname FROM pg_constraint WHERE conrelid=%s::regclass AND contype='f'",(table,)).fetchall():
                    conn.execute(f'ALTER TABLE {table} ALTER CONSTRAINT "{constraint[0]}" DEFERRABLE INITIALLY IMMEDIATE')
            conn.execute('SET CONSTRAINTS ALL DEFERRED')
            for table in tables:
                rows=source.db.execute('SELECT * FROM '+table).fetchall()
                for row in rows:
                    names=list(row.keys())
                    conn.execute('INSERT INTO '+table+' ('+','.join(names)+') VALUES ('+','.join(['%s']*len(names))+')',tuple(row))
        def checksums(connection):
            result={}
            for table in tables:
                rows=connection.execute('SELECT '+('tenant_id,id,assistant_id,conversation_id,external_key,data,created_at' if table in TABLES else '*')+' FROM '+table).fetchall()
                values=[list(row) for row in rows]
                result[table]=sha256(json.dumps(sorted(values,key=lambda row:json.dumps(row,ensure_ascii=False)),ensure_ascii=False).encode()).hexdigest()
            return result
        expected=checksums(source.db)
        with target.pool.connection() as conn:
            if checksums(conn)!=expected:raise RuntimeError('Import checksum mismatch')
        dump=docker('exec','test-mid-phase26c-pg','pg_dump','-U','postgres','-d','phase26c_fixture','--schema',schema,'-Fc')
        docker('exec','test-mid-phase26c-pg','createdb','-U','postgres',restore)
        docker('exec','-i','test-mid-phase26c-pg','pg_restore','--exit-on-error','-U','postgres','-d',restore,input=dump)
        restore_dsn=psycopg.conninfo.make_conninfo(dsn,dbname=restore)
        restored=PostgresStore(restore_dsn,schema=schema,pool_size=2)
        with restored.pool.connection() as conn:
            if checksums(conn)!=expected:raise RuntimeError('Restore checksum mismatch')
        import sqlite3
        entry=restored.list('billing_usage','synthetic-a')[0]
        try:restored.db.execute('DELETE FROM billing_usage WHERE tenant_id=? AND id=?',('synthetic-a',entry['id']))
        except sqlite3.IntegrityError:pass
        else:raise RuntimeError('Restored ledger trigger missing')
        return {'scope':'SYNTHETIC_NATIVE_POSTGRES_MIGRATION','status':'PASS_LOCAL_RUNTIME',
            'import_checksums':'PASS','native_dump_restore_checksums':'PASS','restored_ledger_trigger':'PASS',
            'source_sqlite_integrity':source.db.execute('PRAGMA integrity_check').fetchone()[0],
            'tables':len(tables),'real_data_migrated':False,'production_ready':False}
    finally:
        if restored:restored.close()
        if target:target.close()
        source.close()
        with psycopg.connect(dsn,autocommit=True) as conn:
            conn.execute('DROP SCHEMA IF EXISTS '+schema+' CASCADE')
            conn.execute('DROP DATABASE IF EXISTS '+restore)


if __name__=='__main__':
    report=run();target=ROOT/'artifacts/phase26c/migration-runtime.json';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
