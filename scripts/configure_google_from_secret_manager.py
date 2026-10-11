"""Load owner-authorized OAuth client secrets without logging credential values."""
import json
import subprocess
from urllib.parse import urlsplit, parse_qs
from phase12_local_journey import ROOT, BASE, request

PROJECT = 'strong-keel-468007-r7'
REDIRECT = 'http://127.0.0.1:3017/backend/api/google/oauth/callback'
GCLOUD = r'C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'

def secret(name):
    result = subprocess.run([GCLOUD, 'secrets', 'versions', 'access', 'latest',
                             '--secret=' + name, '--project=' + PROJECT],
                            capture_output=True, text=True, timeout=60)
    if result.returncode or not result.stdout.strip():
        raise RuntimeError('Secret Manager access failed for ' + name)
    return result.stdout.strip()

def main():
    state = json.loads((ROOT / 'artifacts/phase14/demo-state.json').read_text())
    password = (ROOT / 'artifacts/local-demo/secrets/demo_login_password.txt').read_text().strip()
    login = request(BASE, '/api/demo/login', data={'username': 'demo', 'password': password})
    headers = {'Authorization': 'Bearer ' + login['access_token'], 'X-Tenant-ID': state['tenant_id']}
    existing = {row['connection']: row for row in request(BASE, '/api/google', headers)}
    client_id, client_secret = secret('G_CLIENT_ID'), secret('G_CLIENT_SECRET')
    if not client_id.endswith('.apps.googleusercontent.com') or not client_secret:
        raise RuntimeError('Secrets do not contain an OAuth client ID and secret')
    report = {'project': PROJECT, 'redirect_uri': REDIRECT, 'connections': []}
    for kind in ('calendar', 'gmail'):
        if existing.get(kind, {}).get('state') == 'connected':
            report['connections'].append({'connection': kind, 'state': 'connected', 'preserved': True})
            continue
        configured = request(BASE, '/api/google/config', headers, {
            'kind': kind, 'client_id': client_id, 'client_secret': client_secret,
            'redirect_uri': REDIRECT, 'expected_account': 'mariya.manolova92@gmail.com'})
        # Validate construction only; the real browser must start its own cookie-bound flow.
        flow = request(BASE, '/api/google/oauth/' + kind, headers, data={})
        url = urlsplit(flow['authorize_url']); query = parse_qs(url.query)
        assert url.scheme == 'https' and url.hostname == 'accounts.google.com'
        assert query['redirect_uri'] == [REDIRECT]
        assert query['client_id'] == [client_id]
        assert query['code_challenge_method'] == ['S256']
        report['connections'].append({'connection': kind, 'state': configured['state'],
                                      'authorization_flow': 'PASS', 'owner_consent': 'REQUIRED'})
    report['live_operations_authorized'] = request(BASE, '/api/concierge/policy', headers)['operations_authorized']
    (ROOT / 'artifacts/phase14/secret-manager-oauth-validation.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Never print request bodies, provider responses, or subprocess stderr.
        print('Configuration failed: ' + type(error).__name__)
        raise SystemExit(1) from None
