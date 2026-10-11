"""Public API ownership, locale and permission contracts, with Google disconnected."""
import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from semantic_os.backend.assistant.api import create_app
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.domain import AssistantConfig
from semantic_os.backend.assistant.concierge import ConciergePolicy,TOOLS
from semantic_os.backend.assistant.ux import DraftInput,RunInput,ConfirmInput
from semantic_os.backend.assistant.widget import WidgetSettings,WidgetPublish,Redeem

class ConciergeAPITests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict('os.environ',{'WIDGET_PUBLIC_ORIGIN':'http://127.0.0.1:3020','WIDGET_DEMO_SITE_ORIGINS':'http://127.0.0.1:5173'});self.env.start()
        self.store=Store();self.store.seed();self.store.seed('other','other')
        self.app=create_app(store=self.store,demo_enabled=True,demo_token='offline-staff-fixture',encryption_key=Fernet.generate_key().decode())
        self.client=TestClient(self.app);self.actor=self.store.principal('demo-admin','demo')
        self.staff={'Authorization':'Bearer offline-staff-fixture','X-Tenant-ID':'demo'}
        self.app.state.concierge.configure(self.actor,ConciergePolicy(enabled=True,operations_authorized=False,management_origin='http://127.0.0.1:3020'))
        draft=self.app.state.ux.save(self.actor,DraftInput(assistant_id='default',config=AssistantConfig(name='Concierge fixture',instructions='Approved public knowledge only.',public_knowledge_only=True,allowed_tools=[*TOOLS,'EscalateToHuman'],enabled_channels=['web_chat']),business={'name':'Concierge fixture'}))
        for locale in ('bg-BG','en-US'):self.app.state.ux.test(self.actor,draft['id'],RunInput(revision=1,scenario='greeting',locale=locale))
        self.app.state.ux.publish(self.actor,draft['id'],ConfirmInput(revision=1,confirmed=True))
        widget=self.app.state.widget
        row=widget.configure(self.actor,WidgetSettings(assistant_id='default',origins=['http://127.0.0.1:5173'],concierge_enabled=True,booking_enabled=False,greetings={'bg-BG':'Добре дошли','en-US':'Welcome'},privacy_notices={'bg-BG':'Поверителност','en-US':'Privacy'}))
        proof=widget.challenge(self.actor,row['id'],'http://127.0.0.1:5173');widget.fetch_domain=lambda *_:proof['content'];widget.verify(self.actor,row['id'],'http://127.0.0.1:5173');widget.publish(self.actor,row['id'],WidgetPublish(draft_id=draft['id'],confirmed=True))
        self.public_id=row['public_id'];ticket=widget.ticket(self.public_id,'http://127.0.0.1:5173');visitor=widget.redeem(self.public_id,Redeem(ticket=ticket['ticket'],parent_origin='http://127.0.0.1:5173',locale='bg-BG'))
        self.visitor={'Origin':'http://127.0.0.1:3020','Authorization':'Bearer '+visitor['session_token'],'X-Tenant-ID':'other'}

    def tearDown(self):self.client.close();self.app.state.voice_runtime.shutdown();self.store.close();self.env.stop()

    def test_private_google_tokens_and_unknown_tools_are_not_public(self):
        self.assertEqual(self.client.get('/api/google',headers=self.visitor).status_code,401)
        response=self.client.post('/widget/v1/actions/'+self.public_id,headers=self.visitor,json={'tool':'SendMessage','arguments':{},'event_id':'wrong','locale':'bg-BG'})
        self.assertEqual(response.status_code,422)
        self.assertEqual(self.client.get('/widget/v1/concierge/'+self.public_id,headers=self.visitor).json()['booking_available'],False)
        self.assertEqual(self.store.count('appointments','demo'),0)

    def test_business_and_feature_reuse_two_agents_and_persist_once(self):
        for locale in ('bg-BG','en-US'):
            payload={'tool':'ConciergeRequest','arguments':{'action':'feature','name':'Example','email':'','company':'Example','topic':'Approved feature suggestion','impact':'Helpful','consent':True},'event_id':locale,'locale':locale}
            first=self.client.post('/widget/v1/actions/'+self.public_id,headers=self.visitor,json=payload)
            self.assertEqual(first.status_code,200,first.text)
            repeated=self.client.post('/widget/v1/actions/'+self.public_id,headers=self.visitor,json=payload)
            self.assertEqual(repeated.status_code,200,repeated.text)
            self.assertTrue(repeated.json()['duplicate'])
        rows=self.app.state.concierge.rows('demo','concierge_request');self.assertEqual(len(rows),2);self.assertEqual({row['locale'] for row in rows},{'bg-BG','en-US'})
        self.assertEqual(self.app.state.concierge.rows('other','concierge_request'),[])
        handoffs=self.store.list('agent_executions','demo');self.assertTrue(handoffs)
        self.assertEqual({row['handoff']['locale'] for row in handoffs},{'bg-BG','en-US'})

    def test_text_booking_does_not_fall_back_to_fake_calendar(self):
        for index,text in enumerate(('Искам да запиша демонстрация за утре в 15:00.','Book a demo tomorrow at 15:00.')):
            response=self.client.post('/widget/messages/'+self.public_id,headers=self.visitor,json={'content':text,'event_id':str(index),'locale':'bg-BG' if index==0 else 'en-US'})
            self.assertEqual(response.status_code,200,response.text)
            self.assertNotEqual(response.json().get('booking_status'),'completed')
        self.assertEqual(self.store.count('appointments','demo'),0)

    def test_oauth_admin_only_and_no_ownership_by_typed_email(self):
        self.assertEqual(self.client.post('/api/google/oauth/calendar',headers=self.visitor,json={}).status_code,401)
        response=self.client.post('/widget/v1/manage/'+self.public_id,headers={'Origin':'http://127.0.0.1:3020'},json={'token':'not-a-proof'*10,'action':'cancel','event_id':'cancel','locale':'en-US','confirmed':True})
        self.assertEqual(response.status_code,403)
