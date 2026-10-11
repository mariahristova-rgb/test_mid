"""Controlled synthetic ASGI/SQLite benchmark; never opens the live database."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
from time import perf_counter_ns


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--samples',type=int,default=40)
    args=parser.parse_args()
    if not 10 <= args.samples <= 100: parser.error('samples must be 10..100')
    sys.path.insert(0,str(args.source_root.resolve()))
    # Local synthetic benchmark budgets only; production limiter is unchanged.
    os.environ.update(ASSISTANT_RATE_LIMIT_READS='10000',ASSISTANT_RATE_LIMIT_WRITES='10000',ASSISTANT_RATE_LIMIT_AI='10000')
    from fastapi.testclient import TestClient
    from semantic_os.backend.assistant.api import create_app
    from semantic_os.backend.assistant.store import Store
    from semantic_os.backend.assistant.providers import ProviderRegistry
    store=Store();store.seed()
    clock=datetime(2030,10,8,9,tzinfo=timezone.utc)
    app=create_app(store=store,providers=ProviderRegistry(),demo_enabled=True,demo_token='synthetic-benchmark-fixture',clock=lambda:clock)
    client=TestClient(app)
    headers={'Authorization':'Bearer synthetic-benchmark-fixture','X-Tenant-ID':'demo'}
    actor=store.principal('demo-admin','demo')
    for index in range(1000):
        store.add('conversations','demo',{'assistant_id':'default','channel':'web_chat','status':'open','active_locale':'bg-BG','human_escalation':False},id=f'fixture-{index}')
    call=app.state.voice.start(actor,'default','bg-BG')
    paths={'assistants':'/api/assistants','conversation_list':'/api/inbox','conversation_detail':'/api/conversations/fixture-0/messages',
        'call_activity':f"/api/calls/{call['id']}/activity",'operations':'/api/operations'}
    if hasattr(app.state,'ux'): paths['conversation_page']='/api/inbox?limit=50'
    def summarize(values):
        ordered=sorted(values)
        return {'samples':len(values),'p50_ms':ordered[math.ceil(.50*len(values))-1],
            'p95_ms':ordered[math.ceil(.95*len(values))-1],'p99_ms':ordered[math.ceil(.99*len(values))-1]}
    report={'measured_at':datetime.now(timezone.utc).isoformat(),'source_root':str(args.source_root.resolve()),
        'scope':'in_process_ASGI_SQLite_memory_synthetic','conversations':1000,'concurrency':1,'metrics':{},'query_plans':{}}
    try:
        for key,path in paths.items():
            client.get(path,headers=headers).raise_for_status()
            values=[]; sizes=[]
            for _ in range(args.samples):
                start=perf_counter_ns();response=client.get(path,headers=headers)
                values.append(round((perf_counter_ns()-start)/1e6,4));response.raise_for_status();sizes.append(len(response.content))
            report['metrics'][key]={**summarize(values),'response_bytes':max(sizes)}
        statements=[];store.db.set_trace_callback(statements.append)
        client.get('/api/inbox',headers=headers).raise_for_status()
        store.db.set_trace_callback(None)
        report['inbox_read_statements']=sum(sql.lstrip().upper().startswith(('SELECT','WITH')) for sql in statements)
        inbox_query=next((sql for sql in statements if sql.lstrip().upper().startswith('WITH ENRICHED')),None)
        if inbox_query: report['query_plans']['inbox_join']=[list(row) for row in store.db.execute('EXPLAIN QUERY PLAN '+inbox_query)]
        values=[]
        for index in range(args.samples):
            conversation=app.state.orchestrator.conversation(actor,'default')
            from semantic_os.backend.assistant.domain import Incoming
            start=perf_counter_ns()
            for turn,text in enumerate(['Book an appointment tomorrow at 15:00.','My name is John Smith.','Yes, confirm.']):
                result=app.state.orchestrator.inbound(actor,conversation['id'],Incoming(content=text,event_id=f'bench-{index}-{turn}'))
            values.append(round((perf_counter_ns()-start)/1e6,4))
            assert result.get('booking_status')=='completed'
            # Each sample starts from identical free calendar state.
            for booking in store.list('appointments','demo'):
                store.update('appointments','demo',booking['id'],{'status':'cancelled'})
        report['metrics']['booking_three_turns_direct']=summarize(values)
        values=[]
        for index in range(args.samples):
            conversation=app.state.orchestrator.conversation(actor,'default')
            start=perf_counter_ns()
            for turn,text in enumerate(['Book an appointment tomorrow at 15:00.','My name is John Smith.','Yes, confirm.']):
                response=client.post(f"/api/conversations/{conversation['id']}/messages",headers=headers,
                    json={'content':text,'event_id':f'http-bench-{index}-{turn}','locale':'en-US'})
                response.raise_for_status()
            values.append(round((perf_counter_ns()-start)/1e6,4))
            assert response.json()['booking_status']=='completed'
            for booking in store.list('appointments','demo'): store.update('appointments','demo',booking['id'],{'status':'cancelled'})
        report['metrics']['booking_three_turns_http']=summarize(values)
        for table in ('conversations','messages','appointments','operations_events'):
            report['query_plans'][table]=[list(row) for row in store.db.execute(f'EXPLAIN QUERY PLAN SELECT data FROM {table} WHERE tenant_id=? ORDER BY rowid',('demo',))]
        if hasattr(app.state,'ux'):
            from semantic_os.backend.assistant.ux import DraftInput,RunInput
            from semantic_os.backend.assistant.domain import AssistantConfig
            draft=app.state.ux.save(actor,DraftInput(config=AssistantConfig(name='Synthetic',enabled_channels=['web_chat'],allowed_tools=['CheckAvailability','CreateAppointment','EscalateToHuman']),business={'name':'Synthetic'}))
            values=[]
            for _ in range(args.samples):
                start=perf_counter_ns();receipt=app.state.ux.test(actor,draft['id'],RunInput(revision=1,scenario='booking',locale='bg-BG'))
                values.append(round((perf_counter_ns()-start)/1e6,4));assert receipt['verdict']=='PASS'
            report['metrics']['isolated_test_execution']=summarize(values)
    finally:
        client.close();app.state.voice_runtime.shutdown();store.close()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['metrics'],indent=2))


if __name__=='__main__': main()
