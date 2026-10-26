"""Subprocess-only synthetic booking worker; no real provider URL or credential."""
from datetime import datetime
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def run(path):
    import psycopg
    from semantic_os.backend.assistant.postgres_store import PostgresStore
    from semantic_os.backend.assistant.api import create_app
    from semantic_os.backend.assistant.connector_contracts import PlatformOAuthApplication
    from semantic_os.backend.assistant.connector_adapters import OfflineProviderHTTP
    from semantic_os.backend.tests.support.fault_recorder import transport
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    info=psycopg.conninfo.conninfo_to_dict(data['dsn'])
    if os.getenv('PHASE26D_PG_DISPOSABLE')!='true' or info.get('host')!='127.0.0.1' or info.get('port')!='55426' or info.get('dbname')!='phase26c_fixture' or not data['schema'].startswith('fixture_'):
        raise RuntimeError('Disposable Phase26D fixture required')
    store=PostgresStore(data['dsn'],schema=data['schema'],pool_size=2)
    try:
        options={'applications':[PlatformOAuthApplication.model_validate(a) for a in data['applications']],
            'http':OfflineProviderHTTP(transport(data['recorder'])), 'platform_secret':lambda *args:'synthetic-only',
            'verify_identity':lambda *args:'synthetic-account'}
        app=create_app(store=store,demo_enabled=True,demo_token='synthetic-fault-worker',encryption_key=data['key'],clock=lambda:datetime.fromisoformat(data['clock']),customer_oauth_options=options,
            customer_calendar_bindings={'demo':{'subject':'demo-admin','connection_id':data['connection']}})
        bridge=app.state.customer_booking
        fault=data.get('fault','normal')
        if fault=='before_lease':os._exit(90)
        if fault=='after_claim':
            update=store.update
            def claimed(table,tenant,identity,changes):
                row=update(table,tenant,identity,changes)
                if table=='jobs' and changes.get('status')=='running':store.after_transaction(lambda:os._exit(91))
                return row
            store.update=claimed
        if fault=='after_success':bridge.persist_confirmation=lambda *args:os._exit(92)
        bridge.worker()
    finally:store.close()

if __name__=='__main__':run(sys.argv[1])
