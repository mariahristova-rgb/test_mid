"""Customer-owned OAuth with injected synthetic transports; no live providers."""
import unittest
from datetime import datetime,timezone,timedelta
from cryptography.fernet import Fernet
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.security import TenantSecretStore
from semantic_os.backend.assistant.connector_contracts import PlatformOAuthApplication,CustomerConnectionConfig
from semantic_os.backend.assistant.customer_oauth import CustomerOAuthService
from semantic_os.backend.assistant.domain import DomainError

class CustomerOAuthTests(unittest.TestCase):
    def test_unconfigured_service_cannot_start(self):
        store=Store();store.seed()
        try:
            service=CustomerOAuthService(store,TenantSecretStore(store,Fernet.generate_key().decode()))
            with self.assertRaises(DomainError):service.create(store.principal('demo-admin','demo'),CustomerConnectionConfig(provider='google',actions=['availability'],revision=1))
        finally:store.close()

    def setUp(self):
        from semantic_os.backend.assistant.connector_adapters import OfflineProviderHTTP,required_scopes
        import httpx
        self.store=Store();self.store.seed();self.store.seed('other','other')
        self.actor=self.store.principal('demo-admin','demo');self.vault=TenantSecretStore(self.store,Fernet.generate_key().decode())
        self.now=datetime(2026,10,14,tzinfo=timezone.utc);self.calls=[];self.hook=None;self.bad_scope=False
        self.app=PlatformOAuthApplication(provider='google',client_id='synthetic-client',secret_reference='platform:oauth:google:client_secret',redirect_uri='https://staging.example.invalid/backend/api/connectors/oauth/google/callback',allowed_redirects=['https://staging.example.invalid/backend/api/connectors/oauth/google/callback'])
        def handler(request):
            self.calls.append(request)
            if self.hook:self.hook()
            return httpx.Response(200,json={'access_token':'synthetic-access','refresh_token':'synthetic-refresh','scope':'' if self.bad_scope else ' '.join(required_scopes('google',['availability'])),'expires_in':120})
        self.service=CustomerOAuthService(self.store,self.vault,applications=[self.app],http=OfflineProviderHTTP(httpx.MockTransport(handler)),platform_secret=lambda ref:'synthetic-platform-secret',verify_identity=lambda *args:'synthetic-account',clock=lambda:self.now)
    def tearDown(self):self.store.close()
    def begin(self):
        row=self.service.create(self.actor,CustomerConnectionConfig(provider='google',actions=['availability'],revision=1))
        return row,self.service.start(self.actor,row['id'],1)
    def finish(self,row,start):return self.service.complete(self.actor,row['id'],'google',start['state'],start['binding'],'synthetic-code')
    def test_callback_redaction_encryption_and_replay(self):
        import json
        row,start=self.begin();result=self.finish(row,start)
        self.assertEqual(result['state'],'connected_unverified');self.assertEqual(result['verification'],'NOT_TESTED')
        self.assertNotIn('synthetic-access',json.dumps(self.store.list('secrets','demo')))
        self.assertNotIn('synthetic-account',json.dumps(self.service.list(self.actor)))
        with self.assertRaises(DomainError):self.finish(row,start)
        self.assertEqual(len(self.calls),1)
    def test_cross_tenant_binding_provider_expiry_and_config_denied(self):
        row,start=self.begin();other=self.store.principal('other','other')
        for actor,provider,binding in [(other,'google',start['binding']),(self.actor,'google','forged'),(self.actor,'outlook',start['binding'])]:
            with self.assertRaises(DomainError):self.service.complete(actor,row['id'],provider,start['state'],binding,'synthetic-code')
        self.now+=timedelta(minutes=11)
        with self.assertRaises(DomainError):self.finish(row,start)
        self.assertEqual(self.calls,[])
    def test_missing_scope_and_forged_identity_cannot_save_grant(self):
        row,start=self.begin();self.bad_scope=True
        with self.assertRaises(DomainError):self.finish(row,start)
        self.assertIsNone(self.store.find('secrets','demo','customer:tokens:'+row['id']))
        self.bad_scope=False;row,start=self.begin();self.service.verify_identity=lambda *args:None
        with self.assertRaises(DomainError):self.finish(row,start)
        self.assertIsNone(self.store.find('secrets','demo','customer:tokens:'+row['id']))
    def test_disconnect_during_exchange_and_refresh_wins(self):
        row,start=self.begin()
        self.hook=lambda:self.service.disconnect(self.actor,row['id'],start['revision'])
        with self.assertRaises(DomainError):self.finish(row,start)
        self.assertEqual(self.service.row(self.actor,row['id'])['state'],'disconnected')
        self.hook=None;row,start=self.begin();connected=self.finish(row,start);self.now+=timedelta(minutes=3)
        self.hook=lambda:self.service.disconnect(self.actor,row['id'],connected['revision'])
        with self.assertRaises(DomainError):self.service.token(self.actor,row['id'])
        self.assertEqual(self.service.row(self.actor,row['id'])['state'],'disconnected')
        self.assertEqual(self.vault.get('demo','customer:tokens:'+row['id'],self.actor),'{}')
    def test_refresh_claim_and_scope_downgrade(self):
        row,start=self.begin();self.finish(row,start);self.now+=timedelta(minutes=3)
        self.hook=lambda:self.assertRaises(DomainError,self.service.token,self.actor,row['id'])
        self.assertEqual(self.service.token(self.actor,row['id']),'synthetic-access')
        self.hook=None;self.now+=timedelta(minutes=3);self.bad_scope=True
        with self.assertRaises(DomainError):self.service.token(self.actor,row['id'])
        self.assertEqual(self.service.row(self.actor,row['id'])['state'],'reauthorization_required')

    def test_signed_google_identity_nonce_audience_and_signature(self):
        import jwt
        from types import SimpleNamespace
        from cryptography.hazmat.primitives.asymmetric import rsa
        from semantic_os.backend.assistant.customer_oauth import GoogleCustomerIdentity
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        verifier=GoogleCustomerIdentity(SimpleNamespace(get_signing_key_from_jwt=lambda token:SimpleNamespace(key=key.public_key())))
        claims={'iss':'https://accounts.google.com','aud':'synthetic-client','sub':'customer-sub','email_verified':True,'nonce':'bound-nonce','iat':datetime.now(timezone.utc),'exp':datetime.now(timezone.utc)+timedelta(minutes=10)}
        def signed(changes):return {'id_token':jwt.encode({**claims,**changes},key,algorithm='RS256')}
        self.assertEqual(verifier('google',signed({}),'synthetic-client','bound-nonce'),'customer-sub')
        for changes in [{'nonce':'forged'},{'aud':'wrong'},{'iss':'https://attacker.example'},{'email_verified':False},{'sub':''}]:
            with self.assertRaises(DomainError):verifier('google',signed(changes),'synthetic-client','bound-nonce')
    def test_http_routes_disabled_without_server_configuration(self):
        from fastapi.testclient import TestClient
        from semantic_os.backend.assistant.api import create_app
        client=TestClient(create_app(store=self.store,demo_enabled=True,demo_token='synthetic-demo-token',encryption_key=Fernet.generate_key().decode()))
        headers={'Authorization':'Bearer synthetic-demo-token','X-Tenant-ID':'demo'}
        response=client.post('/api/customer-connectors/connections',headers=headers,json={'provider':'google','actions':['availability'],'revision':1})
        self.assertEqual(response.status_code,503)
        self.assertEqual(client.get('/api/customer-connectors/connections',headers=headers).json(),[])

    def test_customer_connections_share_existing_plan_limit(self):
        from semantic_os.backend.assistant.billing import BillingService
        from semantic_os.backend.assistant.saas_domain import SubscriptionPlan
        BillingService(self.store,self.vault,lambda:self.now,demo=True)
        plan=SubscriptionPlan(id='synthetic-plan',name_bg='Тест',name_en='Test',connector_limit=1,connector_providers=['google']).model_dump()
        self.store.add('subscriptions','demo',{'status':'active','plan_snapshot':plan,'period_end':'2099-01-01T00:00:00+00:00'},external_key='current')
        self.begin()
        with self.assertRaises(DomainError):self.begin()

    def test_refresh_claim_survives_a_second_store_instance(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/'synthetic.db');first=Store(path);first.seed()
            key=Fernet.generate_key().decode();vault=TenantSecretStore(first,key)
            opts=dict(applications=[self.app],http=self.service.http,platform_secret=self.service.platform_secret,verify_identity=self.service.verify_identity,clock=lambda:self.now)
            one=CustomerOAuthService(first,vault,**opts);actor=first.principal('demo-admin','demo')
            row=one.create(actor,CustomerConnectionConfig(provider='google',actions=['availability'],revision=1));started=one.start(actor,row['id'],1)
            one.complete(actor,row['id'],'google',started['state'],started['binding'],'synthetic-code')
            second=Store(path);two=CustomerOAuthService(second,TenantSecretStore(second,key),**opts)
            try:
                self.now+=timedelta(minutes=3)
                self.hook=lambda:self.assertRaises(DomainError,two.token,second.principal('demo-admin','demo'),row['id'])
                self.assertEqual(one.token(actor,row['id']),'synthetic-access')
                self.assertIsNone(two.row(actor,row['id']).get('refresh_claim'))
            finally:second.close();first.close()

    def test_resource_discovery_ownership_revision_and_offline_evidence(self):
        from semantic_os.backend.assistant.connector_adapters import OfflineProviderHTTP
        import httpx
        row,start=self.begin();connected=self.finish(row,start)
        self.service.http=OfflineProviderHTTP(httpx.MockTransport(lambda request:httpx.Response(200,json={'items':[{'id':'owned','accessRole':'owner'},{'id':'readonly','accessRole':'reader'}]})))
        with self.assertRaises(DomainError):self.service.select_resources(self.actor,row['id'],connected['revision'],['forged'])
        selected=self.service.select_resources(self.actor,row['id'],connected['revision'],['owned'])
        self.assertEqual(selected['verification'],'OFFLINE_PASS');self.assertEqual(selected['state'],'connected_unverified')
        with self.assertRaises(DomainError):self.service.select_resources(self.actor,row['id'],connected['revision'],['owned'])
        self.service.disconnect(self.actor,row['id'],selected['revision'])
        with self.assertRaises(DomainError):self.service.resources(self.actor,row['id'])

    def test_https_callback_cookie_contract_and_redacted_response(self):
        from fastapi.testclient import TestClient
        from semantic_os.backend.assistant.api import create_app
        from urllib.parse import urlsplit,parse_qs
        app=create_app(store=self.store,demo_enabled=True,demo_token='synthetic-demo-token',encryption_key=Fernet.generate_key().decode(),clock=lambda:self.now,customer_oauth_options={'applications':[self.app],'http':self.service.http,'platform_secret':self.service.platform_secret,'verify_identity':self.service.verify_identity})
        client=TestClient(app,base_url='https://testserver')
        headers={'Authorization':'Bearer synthetic-demo-token','X-Tenant-ID':'demo'}
        row=client.post('/api/customer-connectors/connections',headers=headers,json={'provider':'google','actions':['availability'],'revision':1}).json()
        start=client.post('/api/customer-connectors/connections/'+row['id']+'/authorize',headers=headers,json={'revision':1})
        self.assertEqual(start.status_code,200)
        cookie=start.headers['set-cookie'];self.assertIn('Secure',cookie);self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=lax',cookie)
        self.assertNotIn('binding',start.json());query=parse_qs(urlsplit(start.json()['authorization_url']).query)
        cookie_value=client.cookies.get('customer-oauth-google')
        # Direct app is mounted without /backend in ASGI tests; send the cookie to
        # its declared browser callback path explicitly, as a mounted deployment does.
        callback='/api/connectors/oauth/google/callback'
        result=client.get(callback,params={'state':query['state'][0],'code':'synthetic-code'},headers={'Cookie':'customer-oauth-google='+cookie_value})
        self.assertEqual(result.status_code,200);self.assertEqual(result.headers['cache-control'],'no-store')
        self.assertNotIn('synthetic-access',result.text);self.assertEqual(result.json()['state'],'connected_unverified')
        self.assertEqual(client.get(callback,params={'state':query['state'][0],'code':'synthetic-code'},headers={'Cookie':'customer-oauth-google='+cookie_value}).status_code,401)
