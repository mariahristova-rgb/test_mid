"""Local username/password entry point reuses gated demo identity and tenant membership."""
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from semantic_os.backend.assistant.api import create_app
from semantic_os.backend.assistant.store import Store


class DemoLoginTests(unittest.TestCase):
    def app(self,enabled=True):
        self.store=Store()
        self.application=create_app(store=self.store,demo_enabled=enabled,demo_token='synthetic-private-demo-token')
        self.client=TestClient(self.application)

    def tearDown(self):
        if hasattr(self,'client'):
            self.client.close();self.application.state.voice_runtime.shutdown();self.store.close()

    @patch.dict('os.environ',{'ASSISTANT_DEMO_LOGIN_ENABLED':'true','ASSISTANT_DEMO_LOGIN_PASSWORD':'0000','ASSISTANT_DEMO_LOGIN_TENANT':'demo','ASSISTANT_DEMO_LOGIN_USERNAME':'demo'})
    def test_password_login_and_protected_bootstrap(self):
        self.app()
        bad=self.client.post('/api/demo/login',json={'username':'demo','password':'wrong'})
        self.assertEqual(bad.status_code,401)
        good=self.client.post('/api/demo/login',json={'username':'demo','password':'0000'})
        self.assertEqual(good.status_code,200,good.text)
        session=good.json()
        response=self.client.get('/api/bootstrap',headers={'Authorization':'Bearer '+session['access_token'],'X-Tenant-ID':session['tenant_id']})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['user']['role'],'admin')
        denied=self.client.get('/api/bootstrap',headers={'Authorization':'Bearer '+session['access_token'],'X-Tenant-ID':'unowned'})
        self.assertEqual(denied.status_code,401)

    @patch.dict('os.environ',{'ASSISTANT_DEMO_LOGIN_ENABLED':'false'})
    def test_login_unavailable_without_explicit_local_enablement(self):
        self.app()
        self.assertEqual(self.client.post('/api/demo/login',json={'username':'demo','password':'0000'}).status_code,503)

    @patch.dict('os.environ',{'ASSISTANT_DEMO_LOGIN_ENABLED':'true','ASSISTANT_DEMO_LOGIN_PASSWORD':'0000'})
    def test_non_demo_app_does_not_expose_credentials(self):
        self.app(False)
        self.assertEqual(self.client.post('/api/demo/login',json={'username':'demo','password':'0000'}).status_code,503)

    @patch.dict('os.environ',{'ASSISTANT_DEMO_LOGIN_ENABLED':'true','ASSISTANT_DEMO_LOGIN_PASSWORD':'0000','ASSISTANT_DEMO_LOGIN_TENANT':'demo'})
    def test_external_client_cannot_login(self):
        self.app()
        with TestClient(self.application,client=('198.51.100.1',1234)) as client:
            self.assertEqual(client.post('/api/demo/login',json={'username':'demo','password':'0000'}).status_code,403)
