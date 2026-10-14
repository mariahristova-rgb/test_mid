import unittest
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from urllib.parse import urlsplit,parse_qs
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
import httpx
import jwt
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.security import TenantSecretStore,IdentityService
from semantic_os.backend.assistant.google_owner_login import GoogleOwnerVerifier,GoogleOwnerLogin
from semantic_os.backend.assistant.google_workspace import ACCOUNT
from semantic_os.backend.assistant.domain import DomainError

class GoogleOwnerLoginTests(unittest.TestCase):
    def setUp(self):
        self.store=Store();self.store.seed('stage','offline-owner');self.store.seed('other','other')
        self.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        self.client_id='fixture.apps.googleusercontent.com'
        self.verifier=GoogleOwnerVerifier(self.client_id,jwks=SimpleNamespace(get_signing_key_from_jwt=lambda _:SimpleNamespace(key=self.key.public_key())))
        self.secrets=TenantSecretStore(self.store,Fernet.generate_key().decode())
        self.now=datetime.now(timezone.utc);self.token='';self.request_data=None
        def exchange(request):
            self.request_data=parse_qs(request.content.decode())
            return httpx.Response(200,json={'id_token':self.token,'access_token':'ignored-fake-access-token'})
        self.service=GoogleOwnerLogin(self.store,self.secrets,lambda:self.now,self.verifier,'fake','stage','https://admin.example/backend/api/auth/google/callback',transport=httpx.MockTransport(exchange))
    def tearDown(self):self.store.close()
    def signed(self,**changes):
        claims={'iss':'https://accounts.google.com','aud':self.client_id,'sub':'owner-subject','email':ACCOUNT,'email_verified':True,'iat':datetime.now(timezone.utc),'exp':datetime.now(timezone.utc)+timedelta(hours=1)}
        claims.update(changes);return jwt.encode(claims,self.key,algorithm='RS256',headers={'kid':'fixture'})
    def flow(self):
        url,binding=self.service.start('bg-BG');query=parse_qs(urlsplit(url).query)
        self.token=self.signed(nonce=query['nonce'][0])
        return query,binding
    def test_verified_owner_login_is_cookie_bound_one_use_and_tenant_scoped(self):
        query,binding=self.flow()
        self.assertEqual(query['scope'],['openid email']);self.assertEqual(query['code_challenge_method'],['S256'])
        with self.assertRaises(DomainError):self.service.callback(query['state'][0],'fake-code','wrong-browser')
        ticket=self.service.callback(query['state'][0],'fake-code',binding)
        self.assertIn('code_verifier',self.request_data)
        with self.assertRaises(DomainError):self.service.callback(query['state'][0],'fake-code',binding)
        with self.assertRaises(DomainError):self.service.redeem(ticket,'wrong-browser')
        session=self.service.redeem(ticket,binding)
        self.assertEqual(session['tenant_id'],'stage')
        identity=IdentityService(self.store,verifier=self.verifier)
        self.assertEqual(identity.authenticate('Bearer '+session['access_token'],'stage','testclient').role,'admin')
        with self.assertRaises(DomainError):identity.authenticate('Bearer '+session['access_token'],'other','testclient')
        with self.assertRaises(DomainError):self.service.redeem(ticket,binding)
        for row in self.store.list('secrets','stage'):self.assertNotIn('ignored-fake-access-token',row['encrypted'])
    def test_wrong_email_issuer_audience_verification_and_signature_rejected(self):
        for changes in ({'email':'other@example.invalid'},{'email_verified':False},{'email_verified':'true'},{'iss':'https://attacker.example'},{'aud':'other-client'},{'aud':[self.client_id,'other-client']},{'exp':datetime.now(timezone.utc)-timedelta(minutes=1)}):
            with self.subTest(changes=changes),self.assertRaises(DomainError):self.verifier.verify('Bearer '+self.signed(**changes))
        other_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        token=jwt.encode({'iss':'https://accounts.google.com'},other_key,algorithm='RS256')
        with self.assertRaises(DomainError):self.verifier.verify('Bearer '+token)
    def test_nonce_mismatch_never_grants_membership(self):
        query,binding=self.flow();self.token=self.signed(nonce='wrong-nonce')
        with self.assertRaises(DomainError):self.service.callback(query['state'][0],'fake-code',binding)
        self.assertIsNone(self.store.find('users','stage','google:owner-subject'))
    def test_expired_state_and_ticket_are_rejected_and_purged(self):
        query,binding=self.flow();self.now+=timedelta(minutes=11)
        with self.assertRaises(DomainError):self.service.callback(query['state'][0],'fake-code',binding)
        self.assertEqual(self.service.purge(),1)
        query,binding=self.flow();ticket=self.service.callback(query['state'][0],'fake-code',binding);self.now+=timedelta(seconds=61)
        with self.assertRaises(DomainError):self.service.redeem(ticket,binding)
    def test_existing_role_is_not_upgraded_and_disabled_members_stay_disabled(self):
        member=self.store.add('users','stage',{'subject':'google:owner-subject','role':'viewer','enabled':True,'preferred_locale':'en-US'},external_key='google:owner-subject')
        query,binding=self.flow();ticket=self.service.callback(query['state'][0],'fake-code',binding);self.service.redeem(ticket,binding)
        self.assertEqual(self.store.principal('google:owner-subject','stage').role,'viewer')
        self.store.update('users','stage',member['id'],{'enabled':False})
        query,binding=self.flow()
        with self.assertRaises(DomainError):self.service.callback(query['state'][0],'fake-code',binding)
    def test_https_routes_issue_secure_cookie_and_redeem_fragment_once(self):
        import os
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from semantic_os.backend.assistant.api import create_app
        env={'ASSISTANT_GOOGLE_LOGIN_ENABLED':'true','ASSISTANT_GOOGLE_LOGIN_GCP_PROJECT':'','ASSISTANT_GOOGLE_LOGIN_CLIENT_ID':self.client_id,'ASSISTANT_GOOGLE_LOGIN_CLIENT_SECRET':'fake',
            'ASSISTANT_GOOGLE_LOGIN_TENANT':'stage','ASSISTANT_GOOGLE_LOGIN_REDIRECT_URI':'https://admin.example/backend/api/auth/google/callback','AUTH0_DOMAIN':'','ASSISTANT_UI_ORIGIN':'https://admin.example'}
        with patch.dict(os.environ,env):
            app=create_app(store=self.store,demo_enabled=False,verifier=self.verifier,encryption_key=Fernet.generate_key().decode())
            app.state.owner_login.transport=self.service.transport
            try:
                with TestClient(app,base_url='https://admin.example') as client:
                    started=client.post('/api/auth/google/start',headers={'X-UI-Locale':'bg-BG'})
                    self.assertEqual(started.status_code,200)
                    cookie=started.headers['set-cookie'].lower();self.assertIn('httponly',cookie);self.assertIn('secure',cookie);self.assertIn('samesite=lax',cookie)
                    query=parse_qs(urlsplit(started.json()['authorize_url']).query);self.token=self.signed(nonce=query['nonce'][0])
                    completed=client.get('/api/auth/google/callback',params={'state':query['state'][0],'code':'fake-code'},follow_redirects=False)
                    self.assertEqual(completed.status_code,303);self.assertNotIn(self.token,completed.headers['location'])
                    ticket=parse_qs(urlsplit(completed.headers['location']).fragment)['owner_ticket'][0]
                    redeemed=client.post('/api/auth/google/redeem',json={'ticket':ticket});self.assertEqual(redeemed.status_code,200)
                    self.assertEqual(redeemed.headers['cache-control'],'no-store')
                    self.assertNotEqual(client.post('/api/auth/google/redeem',json={'ticket':ticket}).status_code,200)
            finally:app.state.voice_runtime.shutdown()

if __name__=='__main__':unittest.main()
