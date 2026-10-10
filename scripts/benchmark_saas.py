"""Measured local ASGI/mock workload, not production/provider capacity evidence."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
from time import perf_counter, process_time
import tracemalloc
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from semantic_os.backend.assistant.api import create_app
from semantic_os.backend.assistant.store import Store, uid

def summarize(samples, elapsed, failures):
    ordered = sorted(samples)
    return {'operations': len(samples), 'wall_seconds': elapsed, 'operations_per_second': len(samples) / elapsed,
        'p50_ms': ordered[len(ordered) // 2], 'p95_ms': ordered[min(len(ordered) - 1, int(len(ordered) * .95))],
        'errors': failures, 'error_rate': failures / len(samples)}

def benchmark():
    os.environ.update(ASSISTANT_RATE_LIMIT_READS='10000', ASSISTANT_RATE_LIMIT_WRITES='10000', ASSISTANT_RATE_LIMIT_AI='10000')
    tracemalloc.start(); cpu = process_time()
    with tempfile.TemporaryDirectory() as directory:
        store = Store(Path(directory) / 'fixture.sqlite3')
        app = create_app(store=store, demo_enabled=True, demo_token='synthetic-benchmark-session', encryption_key=Fernet.generate_key().decode())
        headers = {'Authorization': 'Bearer synthetic-benchmark-session', 'X-Tenant-ID': 'demo'}
        client = TestClient(app)
        result = {'environment': {'os': platform.system(), 'python': platform.python_version(), 'logical_cpus': os.cpu_count(),
            'transport': 'in_process_ASGI_testclient', 'database': 'temporary_SQLite_WAL', 'providers': 'MOCK', 'rate_limits': 'raised_only_for_fixture_workload'}, 'workloads': {}}
        try:
            for concurrency in (1, 4, 8):
                def operation(index):
                    start = perf_counter()
                    conversation = client.post('/api/conversations', headers=headers, json={})
                    if conversation.status_code != 201: return (perf_counter() - start) * 1000, True
                    response = client.post('/api/conversations/' + conversation.json()['id'] + '/messages', headers=headers, json={
                        'content': 'Hello', 'event_id': uid(), 'tool': 'CheckAvailability',
                        'arguments': {'starts_at': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(), 'duration_minutes': 30}})
                    return (perf_counter() - start) * 1000, response.status_code != 200
                start = perf_counter()
                with ThreadPoolExecutor(max_workers=concurrency) as pool: measured = list(pool.map(operation, range(30)))
                result['workloads']['conversation_agent_tool_concurrency_' + str(concurrency)] = summarize([m[0] for m in measured], perf_counter() - start, sum(m[1] for m in measured))
            start = perf_counter()
            for _ in range(30): client.get('/api/usage', headers=headers).raise_for_status()
            result['workloads']['indexed_usage_queries'] = {'operations': 30, 'wall_seconds': perf_counter() - start, 'ledger_rows': store.count('billing_usage', 'demo')}
            gateway, principal = app.state.messaging, store.principal('demo-admin', 'demo')
            credential = uid() + uid()
            conn = client.post('/api/messaging/connections', headers=headers, json={'channel': 'sms', 'sender_id': '+359888000001',
                'webhook_secret': credential, 'rate_per_minute': 300}).json()
            start = perf_counter()
            for index in range(10):
                raw = json.dumps({'external_message_id': 'benchmark:' + str(index), 'sender_id': '+359888000002',
                    'recipient_id': conn['sender_id'], 'content': 'Hello', 'timestamp': datetime.now(timezone.utc).isoformat()}).encode()
                gateway.ingest('demo', conn['id'], raw, {'x-signature': hmac.new(credential.encode(), raw, hashlib.sha256).hexdigest()})
            gateway.run(principal); gateway.run(principal)
            result['workloads']['messaging_jobs'] = {'inbound': 10, 'outbound': 10, 'wall_seconds': perf_counter() - start,
                'dead_letters': sum(j['status'] == 'dead_letter' for j in store.list('jobs', 'demo'))}
            store.update('channel_connections', 'demo', conn['id'], {'rate_per_minute': 1})
            conversation = next(c for c in store.list('conversations', 'demo') if c.get('connection_id') == conn['id'])
            gateway.queue_response(principal, store.get('assistants', 'demo', 'default'), conversation, 'Hello', 'en-US', uid())
            gateway.run(principal)
            result['workloads']['provider_rate_limit'] = {'retry_jobs': sum(j['status'] == 'retry' for j in store.list('jobs', 'demo')), 'real_sends': 0}
            def start_call(_):
                response = client.post('/api/calls', headers=headers, json={})
                return response.status_code, response.json()
            with ThreadPoolExecutor(max_workers=8) as pool: calls = list(pool.map(start_call, range(8)))
            result['workloads']['synthetic_call_admission'] = {'attempts': 8, 'accepted': sum(status == 201 for status, _ in calls),
                'rejected': sum(status != 201 for status, _ in calls), 'actual_phone_calls_or_audio_load': False}
            for status, call in calls:
                if status == 201: app.state.voice.finish(principal, call['id'])
            result['resources'] = {'process_cpu_seconds': process_time() - cpu, 'peak_python_allocated_bytes': tracemalloc.get_traced_memory()[1],
                'database_file_bytes': (Path(directory) / 'fixture.sqlite3').stat().st_size}
            result['limitations'] = ['Single process and one SQLite writer lock', 'TestClient/tracemalloc overhead is included',
                'No real LLM/speech/carrier/payment requests', 'Python allocation peak is not OS RSS', 'No production capacity or SLA conclusion']
            return result
        finally: client.close(); store.close(); tracemalloc.stop()
if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path); args = parser.parse_args()
    result = benchmark(); data = json.dumps(result, indent=2)
    if args.output: args.output.write_text(data + '\n', encoding='utf-8'); print('Measured local mock benchmark written; no production capacity claim.')
    else: print(data)
