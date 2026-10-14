"""Production identity codecs verified using signed synthetic tokens and mock HTTP."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from semantic_os.backend.assistant.connector_adapters import OfflineProviderHTTP
from semantic_os.backend.assistant.provider_identity import ProviderIdentityVerifier
from semantic_os.backend.assistant.domain import DomainError


class ProviderIdentityTests(unittest.TestCase):
    def setUp(self):
        self.response={};self.calls=[]
        self.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        self.tenant='11111111-1111-4111-8111-111111111111'
        def handle(request):
            self.calls.append(request)
            return httpx.Response(200,json=self.response)
        self.verifier=ProviderIdentityVerifier(OfflineProviderHTTP(httpx.MockTransport(handle)),lambda ref:'synthetic-secret',
            outlook_jwks=SimpleNamespace(get_signing_key_from_jwt=lambda token:SimpleNamespace(key=self.key.public_key())),
            outlook_tenants=[self.tenant])

    def signed(self,**changes):
        claims={'iss':'https://login.microsoftonline.com/'+self.tenant+'/v2.0','aud':'synthetic-client',
                'sub':'synthetic-account','oid':'33333333-3333-4333-8333-333333333333','tid':self.tenant,'nonce':'synthetic-nonce',
                'iat':datetime.now(timezone.utc),'exp':datetime.now(timezone.utc)+timedelta(minutes=10)}
        claims.update(changes)
        return {'id_token':jwt.encode(claims,self.key,algorithm='RS256')}

    def test_outlook_signature_nonce_audience_and_tenant_policy(self):
        self.assertEqual(self.verifier('outlook',self.signed(),'synthetic-client','synthetic-nonce'),self.tenant+':33333333-3333-4333-8333-333333333333')
        for changes in ({'nonce':'forged'},{'aud':'wrong-client'},{'iss':'https://attacker.example'},
                        {'tid':'22222222-2222-4222-8222-222222222222'},{'sub':''}):
            with self.subTest(changes=changes),self.assertRaises(DomainError):
                self.verifier('outlook',self.signed(**changes),'synthetic-client','synthetic-nonce')

    def test_hubspot_active_client_bound_account_and_scopes(self):
        self.response={'active':True,'client_id':'synthetic-client','token_use':'access_token','hub_id':123,'scopes':['oauth','crm.objects.contacts.read']}
        tokens={'access_token':'synthetic-token'}
        self.assertEqual(self.verifier('hubspot',tokens,'synthetic-client','nonce'),'123')
        self.assertEqual(tokens['scope'],'oauth crm.objects.contacts.read')
        for key,value in [('active',False),('client_id','other-client'),('token_use','refresh_token'),('hub_id',True),('scopes','oauth')]:
            original=self.response.copy();self.response[key]=value
            with self.subTest(key=key),self.assertRaises(DomainError):self.verifier('hubspot',{'access_token':'synthetic-token'},'synthetic-client','nonce')
            self.response=original

    def test_calendly_authenticated_resource_uri_not_arbitrary_url(self):
        uri='https://api.calendly.com/users/11111111-1111-4111-8111-111111111111'
        self.response={'resource':{'uri':uri}}
        self.assertEqual(self.verifier('calendly',{'access_token':'synthetic-token'},'client','nonce'),uri)
        self.assertEqual(self.calls[0].url.host,'api.calendly.com')
        for value in ('https://attacker.example/users/11111111-1111-4111-8111-111111111111',uri+'/extra','fixture-account'):
            self.response={'resource':{'uri':value}}
            with self.assertRaises(DomainError):self.verifier('calendly',{'access_token':'synthetic-token'},'client','nonce')

    def test_unconfigured_identity_is_not_advertised_as_available(self):
        self.assertFalse(self.verifier.supports('google'));self.assertTrue(self.verifier.supports('outlook'))
        self.assertFalse(ProviderIdentityVerifier(None,None).supports('calendly'))

    def test_outlook_personal_calendar_view_and_incomplete_results_fail_closed(self):
        from semantic_os.backend.assistant.connector_adapters import ProductionProviderAdapter
        self.response={'value':[{'showAs':'busy','isAllDay':True}]}
        adapter=ProductionProviderAdapter('outlook',self.verifier.http)
        args={'start':'2026-10-15T12:00:00+00:00','end':'2026-10-15T12:30:00+00:00'}
        result=adapter.execute('synthetic-token','availability','calendar-id',args,'synthetic-key',account_type='personal')
        self.assertFalse(result['available']);self.assertIn('/calendarView',self.calls[-1].url.path)
        self.response={'value':[],'@odata.nextLink':'https://graph.microsoft.com/v1.0/more'}
        with self.assertRaises(DomainError):adapter.execute('synthetic-token','availability','calendar-id',args,'synthetic-key')
        self.response={'value':[]};self.assertTrue(adapter.execute('synthetic-token','availability','calendar-id',args,'synthetic-key')['available'])
        with self.assertRaises(DomainError):adapter.execute('synthetic-token','availability','calendar-id',args,'synthetic-key',account_type='shared')

    def test_refresh_identity_cannot_change_bound_account(self):
        tokens={'access_token':'synthetic-token'}
        self.response={'sub':'synthetic-google-subject','email_verified':True}
        self.assertEqual(self.verifier.refresh('google',tokens,'client','synthetic-google-subject'),'synthetic-google-subject')
        with self.assertRaises(DomainError):self.verifier.refresh('google',tokens,'client','other-account')
        self.response={'id':'33333333-3333-4333-8333-333333333333'}
        self.assertEqual(self.verifier.refresh('outlook',tokens,'client',self.tenant+':33333333-3333-4333-8333-333333333333'),self.tenant+':33333333-3333-4333-8333-333333333333')
        with self.assertRaises(DomainError):self.verifier.refresh('outlook',tokens,'client',self.tenant+':44444444-4444-4444-8444-444444444444')
