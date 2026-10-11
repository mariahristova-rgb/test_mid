"""Fixed two-secret, metadata-identity credential loading for an isolated GCE host."""
import base64
import re
import httpx

def owner_oauth_credentials(project):
    if not re.fullmatch(r'[a-z][a-z0-9-]{4,61}[a-z0-9]',project):raise RuntimeError('A Google project ID is required')
    try:
        with httpx.Client(timeout=10,trust_env=False,follow_redirects=False) as client:
            response=client.get('http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token',headers={'Metadata-Flavor':'Google'})
            response.raise_for_status();token=response.json()['access_token']
            result=[]
            for name in ('G_CLIENT_ID','G_CLIENT_SECRET'):
                response=client.get('https://secretmanager.googleapis.com/v1/projects/'+project+'/secrets/'+name+'/versions/latest:access',headers={'Authorization':'Bearer '+token})
                response.raise_for_status()
                if len(response.content)>20000:raise RuntimeError('Credential response too large')
                value=base64.b64decode(response.json()['payload']['data'],validate=True).decode().strip()
                if not value or len(value)>4096:raise RuntimeError('Invalid credential material')
                result.append(value)
            return tuple(result)
    except Exception:raise RuntimeError('Owner OAuth credentials unavailable; no fallback identity is allowed') from None
