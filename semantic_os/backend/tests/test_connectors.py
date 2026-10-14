"""Local connector contracts; no network, real credentials or provider mutations."""
import json
import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from semantic_os.backend.assistant.api import create_app
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.connectors import ConnectorService,ConnectionInput,ConnectionAction,CAPABILITIES,ProviderPreview,QuoteInput
from semantic_os.backend.assistant.security import TenantSecretStore
from semantic_os.backend.assistant.domain import DomainError,Principal

class ConnectorTests(unittest.TestCase):
    def setUp(self):
        self.store=Store();self.store.seed();self.store.seed('other','other')
        self.actor=self.store.principal('demo-admin','demo')
        self.secrets=TenantSecretStore(self.store,Fernet.generate_key().decode())
        self.service=ConnectorService(self.store,self.secrets,enabled=True)
    def tearDown(self):self.store.close()
    def create(self,provider='google'):
        return self.service.create(self.actor,ConnectionInput(provider=provider,actions=[CAPABILITIES[provider][0]],resource_ids=['fixture-primary']))

    def test_bilingual_all_provider_lifecycle_encryption_and_zero_effects(self):
        with patch('httpx.Client',side_effect=AssertionError('external I/O prohibited')):
            for provider in CAPABILITIES:
                for locale in ('bg-BG','en-US'):
                    row=self.create(provider)
                    for scenario,state in [('connect','connected'),('expired','needs_reauthorization'),('connect','connected'),('failure','degraded')]:
                        row=self.service.test(self.actor,row['id'],ConnectionAction(revision=row['revision'],scenario=scenario,locale=locale))
                        self.assertEqual(row['state'],state);self.assertEqual(row['locale'],locale)
                    row=self.service.disconnect(self.actor,row['id'],ConnectionAction(revision=row['revision']))
                    self.assertEqual(row['state'],'disconnected')
            self.assertNotIn('fixture-token',json.dumps(self.store.list('secrets','demo')))
            self.assertEqual(self.store.list('appointments','demo'),[])
            self.assertEqual(self.store.list('jobs','demo'),[])
            self.assertEqual(self.store.list('billing_invoices','demo'),[])

    def test_tenant_role_revision_and_unknown_outcome_invariants(self):
        row=self.create();other=self.store.principal('other','other')
        for principal in (other,Principal('demo','visitor','viewer','visitor')):
            with self.assertRaises(DomainError):self.service.test(principal,row['id'],ConnectionAction(revision=1))
        row=self.service.test(self.actor,row['id'],ConnectionAction(revision=1,scenario='unknown'))
        with self.assertRaises(DomainError):self.service.test(self.actor,row['id'],ConnectionAction(revision=1))
        with self.assertRaises(DomainError):self.service.test(self.actor,row['id'],ConnectionAction(revision=2))
        row=self.service.disconnect(self.actor,row['id'],ConnectionAction(revision=2))
        self.assertEqual(row['failure_code'],'delivery_unknown')
        with self.assertRaises(DomainError):self.service.test(self.actor,row['id'],ConnectionAction(revision=3))
        self.assertEqual(self.store.list('operations_events','other'),[])

    def test_invalid_capabilities_resources_and_default_disable(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):ConnectionInput(provider='google',actions=['create'],resource_ids=['https://example.com'])
        with self.assertRaises(ValidationError):ConnectionInput(provider='google',actions=['create'],resource_ids=['fixture-primary'],token='real')
        with self.assertRaises(DomainError):self.service.create(self.actor,ConnectionInput(provider='hubspot',actions=['create'],resource_ids=['fixture-primary']))
        with self.assertRaises(DomainError):ConnectorService(self.store,self.secrets).create(self.actor,ConnectionInput(provider='google',actions=['create'],resource_ids=['fixture-primary']))

    def test_create_replay_and_mutation_revision_prevent_duplicates(self):
        first=self.create();second=self.create()
        self.assertEqual(first['id'],second['id'])
        result=self.service.test(self.actor,first['id'],ConnectionAction(revision=1))
        with self.assertRaises(DomainError):self.service.test(self.actor,first['id'],ConnectionAction(revision=1))
        self.assertEqual(self.create()['revision'],result['revision'])
        self.assertEqual(len(self.service.list(self.actor)),1)

    def test_reviewed_api_contract_and_legacy_google_compatibility(self):
        app=create_app(store=self.store,demo_enabled=True,demo_token='fixture-only',encryption_key=Fernet.generate_key().decode(),connector_fixtures=True)
        client=TestClient(app);headers={'Authorization':'Bearer fixture-only','X-Tenant-ID':'demo'}
        self.assertEqual(client.get('/api/connectors').status_code,401)
        self.assertEqual(client.get('/api/connectors',headers=headers).status_code,200)
        created=client.post('/api/connectors/connections',headers=headers,json={'provider':'google','actions':['availability'],'resource_ids':['fixture-primary']})
        self.assertEqual(created.status_code,200);row=created.json()
        response=client.post('/api/connectors/connections/'+row['id']+'/test',headers=headers,json={'revision':1,'locale':'bg-BG'})
        self.assertEqual(response.status_code,200);self.assertTrue(response.json()['simulation'])
        self.assertEqual(client.get('/api/google',headers=headers).json(),[])
        self.assertNotIn('token',json.dumps(client.get('/api/connectors/connections',headers=headers).json()))

    def oauth_connect(self,provider):
        row=self.service.create(self.actor,ConnectionInput(provider=provider,actions=CAPABILITIES[provider],resource_ids=['fixture-primary']))
        start=self.service.oauth.start(self.actor,row['id'],row['revision'])
        connected=self.service.oauth.complete(self.actor,row['id'],start['state'],start['binding'],'fixture-code')
        return connected,start

    def test_provider_oauth_discovery_and_all_supported_actions_bilingual(self):
        for provider in CAPABILITIES:
            row,start=self.oauth_connect(provider)
            self.assertTrue(start['simulation']);self.assertNotIn('secret',start['authorization_preview'])
            self.assertEqual(row['state'],'connected')
            self.assertTrue(self.service.resources(self.actor,row['id'])['resources'])
            for locale in ('bg-BG','en-US'):
                for action in CAPABILITIES[provider]:
                    args={'start':'2030-10-09T15:00:00+03:00','end':'2030-10-09T15:30:00+03:00','event_id':'fixture-owned','etag':'fixture-etag',
                          'properties':{'email':'synthetic@example.invalid','firstname':'Synthetic','company':'Fixture'}}
                    payload=ProviderPreview(revision=row['revision'],action=action,resource_id='fixture-primary',key=locale+action,consent=True,arguments=args,locale=locale)
                    result=self.service.preview(self.actor,row['id'],payload)
                    self.assertTrue(result['simulation']);self.assertEqual(result['locale'],locale)
                    self.assertEqual(result,self.service.preview(self.actor,row['id'],payload))
                    if action=='availability':self.assertTrue(result['available'])
            self.assertNotIn('fixture-access',json.dumps(self.service.list(self.actor)))
        self.assertEqual(self.store.list('appointments','demo'),[])
        self.assertEqual(self.store.list('jobs','demo'),[])
        self.assertEqual(self.store.list('billing_invoices','demo'),[])

    def test_oauth_state_tenant_user_expiry_replay_and_disconnect(self):
        from datetime import datetime,timedelta,timezone
        at=datetime(2030,1,1,tzinfo=timezone.utc);self.service.clock=lambda:at;self.service.oauth.clock=lambda:at
        row=self.create();start=self.service.oauth.start(self.actor,row['id'],1)
        other=self.store.principal('other','other')
        for actor,binding in ((other,start['binding']),(self.actor,'incorrect-binding')):
            with self.assertRaises(DomainError):self.service.oauth.complete(actor,row['id'],start['state'],binding,'fixture-code')
        row=self.service.oauth.complete(self.actor,row['id'],start['state'],start['binding'],'fixture-code')
        with self.assertRaises(DomainError):self.service.oauth.complete(self.actor,row['id'],start['state'],start['binding'],'fixture-code')
        start=self.service.oauth.start(self.actor,row['id'],row['revision'])
        at+=timedelta(minutes=11)
        with self.assertRaises(DomainError):self.service.oauth.complete(self.actor,row['id'],start['state'],start['binding'],'fixture-code')
        self.service.disconnect(self.actor,row['id'],ConnectionAction(revision=row['revision']))
        with self.assertRaises(DomainError):self.service.resources(self.actor,row['id'])
        self.assertEqual(json.loads(self.secrets.get('demo','connector:oauth:'+row['id'])),{})

    def test_scopes_refresh_rotation_and_unknown_provider_write_no_replay(self):
        import httpx
        from datetime import timedelta
        row,_=self.oauth_connect('calendly')
        token_key='connector:oauth:'+row['id'];before=json.loads(self.secrets.get('demo',token_key))
        before['expires_at']='2000-01-01T00:00:00+00:00';self.secrets.put('demo',token_key,json.dumps(before))
        self.service.oauth.token(self.actor,row)
        after=json.loads(self.secrets.get('demo',token_key));self.assertNotEqual(before['refresh_token'],after['refresh_token'])
        from semantic_os.backend.assistant.connector_adapters import OfflineProviderHTTP
        google,_=self.oauth_connect('google');attempts=[]
        def timeout(request):
            attempts.append(str(request.url));raise httpx.ReadTimeout('fixture timeout')
        self.service.http=OfflineProviderHTTP(httpx.MockTransport(timeout))
        payload=ProviderPreview(revision=google['revision'],action='create',resource_id='fixture-primary',key='unknown',consent=True,
                                arguments={'start':'2030-10-09T12:00:00Z','end':'2030-10-09T12:30:00Z'})
        with self.assertRaises(DomainError) as caught:self.service.preview(self.actor,google['id'],payload)
        self.assertEqual(caught.exception.code,'delivery_unknown');self.assertEqual(len(attempts),1)
        payload.revision+=1
        with self.assertRaises(DomainError):self.service.preview(self.actor,google['id'],payload)
        self.assertEqual(len(attempts),1)

    def test_provider_permission_mapping_personal_outlook_and_stale_etag(self):
        from semantic_os.backend.assistant.connector_adapters import ProviderAdapter
        args={'start':'2030-10-09T12:00:00Z','end':'2030-10-09T12:30:00Z'}
        outlook=ProviderAdapter('outlook',self.service.http)
        with self.assertRaises(DomainError):outlook.execute('fake','availability','fixture-primary',args,'key',account_type='personal')
        with self.assertRaises(DomainError):outlook.execute('fake','create','fixture-primary',args,'key',owned=True,consent=False)
        with self.assertRaises(DomainError):outlook.execute('fake','reschedule','fixture-primary',{**args,'event_id':'fixture-event'},'key',owned=True,consent=True)
        hubspot=ProviderAdapter('hubspot',self.service.http)
        with self.assertRaises(DomainError):hubspot.execute('fake','contact_write','fixture-primary',{'properties':{'email':'synthetic@example.invalid','secret':'bad'}},'key',owned=True,consent=True)
        with self.assertRaises(DomainError):ProviderAdapter('calendly',self.service.http).execute('fake','create','fixture-primary',{},'key',owned=True,consent=True)

    def test_calendly_signed_webhook_replay_stale_wrong_resource(self):
        import hmac
        row,_=self.oauth_connect('calendly');stamp=str(int(self.service.clock().timestamp()))
        raw=json.dumps({'event':'invitee.created','payload':{'event':'fixture-primary'}}).encode()
        signature=hmac.new(b'fixture-webhook-secret',stamp.encode()+b'.'+raw,'sha256').hexdigest();header='t='+stamp+',v1='+signature
        self.assertFalse(self.service.webhook(self.actor,row['id'],raw,header)['duplicate'])
        self.assertTrue(self.service.webhook(self.actor,row['id'],raw,header)['duplicate'])
        with self.assertRaises(DomainError):self.service.webhook(self.actor,row['id'],raw,header.replace(signature,'0'*64))
        with self.assertRaises(DomainError):self.service.webhook(self.actor,row['id'],raw,header.replace(stamp,'1'))
        wrong=json.dumps({'event':'invitee.created','payload':{'event':'fixture-other'}}).encode()
        wrong_signature=hmac.new(b'fixture-webhook-secret',stamp.encode()+b'.'+wrong,'sha256').hexdigest()
        with self.assertRaises(DomainError):self.service.webhook(self.actor,row['id'],wrong,'t='+stamp+',v1='+wrong_signature)

    def test_connection_and_quote_restore_with_existing_store(self):
        import tempfile
        from pathlib import Path
        key=Fernet.generate_key().decode()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'synthetic.sqlite'
            first=Store(path);first.seed();actor=first.principal('demo-admin','demo')
            service=ConnectorService(first,TenantSecretStore(first,key),enabled=True)
            row=service.create(actor,ConnectionInput(provider='google',actions=['availability'],resource_ids=['fixture-primary']))
            start=service.oauth.start(actor,row['id'],row['revision'])
            service.oauth.complete(actor,row['id'],start['state'],start['binding'],'fixture-code')
            quote=service.quote(actor,QuoteInput(tier='simple',system='rest',objects=['contacts'],direction='one_way',authentication='oauth',environments=1,key='restore'))
            first.close()
            restored=Store(path)
            try:
                service=ConnectorService(restored,TenantSecretStore(restored,key),enabled=True)
                actor=restored.principal('demo-admin','demo')
                self.assertEqual(service.list(actor)[0]['state'],'connected')
                self.assertEqual(service.quotes(actor)[0]['id'],quote['id'])
                self.assertTrue(service.resources(actor,row['id'])['simulation'])
            finally:restored.close()

    def test_entitlements_and_quote_workflow_do_not_charge(self):
        from semantic_os.backend.assistant.billing import BillingService
        from semantic_os.backend.assistant.saas_domain import SubscriptionPlan
        billing=BillingService(self.store,self.secrets,self.service.clock,demo=True)
        plan=SubscriptionPlan(id='fixture',name_bg='Тест',name_en='Test',connector_limit=1,connector_providers=['google']).model_dump()
        self.store.add('subscriptions','demo',{'status':'active','plan_snapshot':plan,'period_end':'2099-01-01T00:00:00+00:00'},external_key='current')
        row=self.create();self.assertEqual(self.create()['id'],row['id'])
        with self.assertRaises(DomainError):self.create('outlook')
        with self.assertRaises(DomainError):self.service.create(self.actor,ConnectionInput(provider='google',actions=['create'],resource_ids=['fixture-second']))
        start=self.service.oauth.start(self.actor,row['id'],row['revision'])
        subscription=billing.entitlements.subscription('demo')
        self.store.update('subscriptions','demo',subscription['id'],{'plan_snapshot':{**plan,'connector_providers':[]}})
        with self.assertRaises(DomainError):self.service.oauth.complete(self.actor,row['id'],start['state'],start['binding'],'fixture-code')
        for tier,maintenance in [('simple',99),('advanced',199),('enterprise',None)]:
            payload=QuoteInput(tier=tier,system='erp',objects=['contacts'],direction='one_way',authentication='oauth',environments=1,key=tier)
            quote=self.service.quote(self.actor,payload)
            self.assertEqual(quote['pricing']['maintenance_eur'],maintenance)
            self.assertFalse(quote['commercial_approval']);self.assertTrue(quote['subscription_separate'])
            self.assertEqual(quote['id'],self.service.quote(self.actor,payload)['id'])
        self.assertEqual(len(self.service.quotes(self.actor)),3)
        self.assertEqual(self.store.list('billing_invoices','demo'),[])

    def test_provider_wire_contracts_and_crm_duplicate_contact(self):
        import httpx
        from semantic_os.backend.assistant.connector_adapters import ProviderAdapter,OfflineProviderHTTP
        from semantic_os.backend.assistant.connector_fixtures import fixture_transport
        delegate=fixture_transport();requests=[]
        def inspect(request):requests.append(request);return delegate.handle_request(request)
        adapter_http=OfflineProviderHTTP(httpx.MockTransport(inspect))
        args={'start':'2030-10-09T15:00:00+03:00','end':'2030-10-09T15:30:00+03:00'}
        ProviderAdapter('google',adapter_http).execute('fake','create','fixture-primary',args,'same-key',owned=True,consent=True)
        body=json.loads(requests[-1].content);self.assertEqual(len(body['id']),64)
        self.assertEqual(requests[-1].url.params['sendUpdates'],'none')
        ProviderAdapter('outlook',adapter_http).execute('fake','create','fixture-primary',args,'same-key',owned=True,consent=True)
        body=json.loads(requests[-1].content);self.assertEqual(body['transactionId'],'same-key')
        self.assertEqual(body['start'],{'dateTime':'2030-10-09T12:00:00','timeZone':'UTC'})
        hubspot=ProviderAdapter('hubspot',adapter_http);properties={'properties':{'email':'fixture@example.invalid','firstname':'Synthetic'}}
        for key in ('first','second'):hubspot.execute('fake','contact_write','fixture-primary',properties,key,owned=True,consent=True)
        self.assertEqual(sum(request.method=='POST' and request.url.path=='/crm/v3/objects/contacts' for request in requests),1)
        self.assertEqual(sum(request.method=='PATCH' and request.url.path.endswith('/fixture-contact') for request in requests),1)

    def test_missing_oauth_scopes_account_mismatch_and_live_transport_refused(self):
        import httpx
        from semantic_os.backend.assistant.connector_adapters import OfflineProviderHTTP
        from semantic_os.backend.assistant.connector_fixtures import fixture_transport
        with self.assertRaises(DomainError):OfflineProviderHTTP(httpx.HTTPTransport())
        row=self.create();start=self.service.oauth.start(self.actor,row['id'],1)
        self.service.oauth.http=OfflineProviderHTTP(httpx.MockTransport(lambda req:httpx.Response(200,json={'access_token':'fake','refresh_token':'fake','expires_in':3600,'scope':'openid'})))
        with self.assertRaises(DomainError):self.service.oauth.complete(self.actor,row['id'],start['state'],start['binding'],'fixture-code')
        self.assertEqual(self.service.row(self.actor,row['id'])['state'],'disconnected')

        delegate=fixture_transport()
        def mismatched(req):
            if req.url.path.endswith('/userinfo'):return httpx.Response(200,json={'email':'wrong@example.invalid','email_verified':True})
            return delegate.handle_request(req)
        self.service.oauth.http=OfflineProviderHTTP(httpx.MockTransport(mismatched))
        start=self.service.oauth.start(self.actor,row['id'],1)
        with self.assertRaises(DomainError):self.service.oauth.complete(self.actor,row['id'],start['state'],start['binding'],'fixture-code')
        self.assertEqual(self.service.row(self.actor,row['id'])['state'],'disconnected')

    def test_disconnect_during_oauth_exchange_cannot_restore_connection(self):
        import httpx
        from semantic_os.backend.assistant.connector_adapters import OfflineProviderHTTP
        from semantic_os.backend.assistant.connector_fixtures import fixture_transport
        row=self.create();start=self.service.oauth.start(self.actor,row['id'],1)
        delegate=fixture_transport()
        def interrupted(request):
            if request.url.path.endswith('/token'):
                self.service.disconnect(self.actor,row['id'],ConnectionAction(revision=1))
            return delegate.handle_request(request)
        self.service.oauth.http=OfflineProviderHTTP(httpx.MockTransport(interrupted))
        with self.assertRaises(DomainError):self.service.oauth.complete(self.actor,row['id'],start['state'],start['binding'],'fixture-code')
        self.assertEqual(self.service.row(self.actor,row['id'])['state'],'disconnected')
        self.assertEqual(json.loads(self.secrets.get('demo','connector:oauth:'+row['id'])),{})

    def test_fixture_api_is_disabled_without_explicit_flag(self):
        app=create_app(store=self.store,demo_enabled=True,demo_token='fixture-disabled',encryption_key=Fernet.generate_key().decode())
        with TestClient(app) as client:
            headers={'Authorization':'Bearer fixture-disabled','X-Tenant-ID':'demo'}
            response=client.get('/api/connectors',headers=headers)
            self.assertEqual(response.status_code,503)
