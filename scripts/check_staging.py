"""Loopback HTTPS staging and restoration rehearsal with synthetic identity only."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import ssl
import subprocess
from time import perf_counter
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from uuid import uuid4
import jwt
from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parents[1]
directory = ROOT / 'artifacts/staging'
session = json.loads((directory / 'session.json').read_text())
context = ssl.create_default_context(cafile=str(directory / 'staging.crt'))
origin = session['origin']
assert origin == 'https://127.0.0.1:8443'

def call(path, data=None, token=None, tenant='staging'):
    request = Request(origin + '/backend' + path, data=json.dumps(data).encode() if data is not None else None,
        headers={'Authorization': 'Bearer ' + (token or session['token']), 'X-Tenant-ID': tenant, 'Content-Type': 'application/json'})
    with urlopen(request, context=context, timeout=10) as response: return response.status, json.loads(response.read())

assert call('/health/ready')[0] == 200
with urlopen(origin, context=context, timeout=10) as response:
    assert response.status == 200 and 'Content-Security-Policy' in response.headers
checks = {'https_certificate_validation': True, 'readiness': True, 'frontend_headers': True, 'channels': {}}
for locale, content in [('bg-BG', 'Здравейте'), ('en-US', 'Hello')]:
    _, conversation = call('/api/conversations', {})
    _, message = call('/api/conversations/' + conversation['id'] + '/messages', {'content': content, 'event_id': str(uuid4()), 'locale': locale})
    assert message['locale'] == locale and message['state'] == 'MOCK'
    checks['channels'][locale] = 'shared_conversation_verified'
key = serialization.load_pem_private_key((directory / 'signing.key').read_bytes(), password=None)
at = datetime.now(timezone.utc)
stranger = jwt.encode({'sub': 'staging-stranger', 'iss': 'https://identity.staging.example.invalid/', 'aud': 'staging-api', 'iat': at, 'exp': at + timedelta(minutes=5)}, key, algorithm='RS256')
try: call('/api/conversations', token=stranger)
except HTTPError as error: assert error.code == 401
else: raise AssertionError('Cross-tenant subject was accepted')
checks['tenant_isolation'] = True
_, billing = call('/api/billing')
assert billing['state'] == 'MOCK' and not billing['real_charges_enabled']
start = perf_counter()
_, backup = call('/api/backups', {'confirmed': True})
program = '''import json,os,sys,threading
from types import SimpleNamespace
from backend.assistant.backup import BackupManager
from backend.assistant.store import Store
manager=BackupManager(SimpleNamespace(db=None,lock=threading.RLock()),"/backups",os.environ["ASSISTANT_BACKUP_ENCRYPTION_KEY"])
result=manager.restore(sys.argv[1],sys.argv[2])
store=Store(sys.argv[2])
assert store.count("messages","staging") >= 4
assert store.count("billing_usage","staging") >= 4
assert not store.db.execute("PRAGMA foreign_key_check").fetchall()
store.close()
print(json.dumps(result))'''
command = ['docker', 'compose', '--env-file', str(directory / 'staging.env'), '-f', str(ROOT / 'semantic_os/deploy/compose.staging.yml'),
    'exec', '-T', 'backend', 'python', '-c', program, backup['filename'], '/data/restore-drill-' + str(uuid4()) + '.sqlite3']
completed = subprocess.run(command, capture_output=True, text=True)
if completed.returncode: raise RuntimeError(completed.stderr)
checks['recovery'] = json.loads(completed.stdout)
checks['observed_backup_restore_seconds'] = perf_counter() - start
checks['rpo_target_seconds'], checks['rto_target_seconds'] = backup['rpo_target_seconds'], backup['rto_target_seconds']
_, operations = call('/api/operations')
checks['worker'] = operations['worker']
checks['limitations'] = ['Local Docker only', 'Self-signed fixture certificate', 'Synthetic JWT issuer/JWKS', 'Mock payment/channel providers', 'Not a production readiness or capacity claim']
(ROOT / 'docs/architecture/STAGING_VERIFICATION.json').write_text(json.dumps(checks, indent=2) + '\n', encoding='utf-8')
print('HTTPS staging, tenant isolation, bilingual conversation, billing and encrypted restoration checks passed.')
