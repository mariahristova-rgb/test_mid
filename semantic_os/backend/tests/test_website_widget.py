"""Website presentation reuses the existing scoped widget contracts."""
import unittest


class WebsiteWidgetTests(unittest.TestCase):
    def setUp(self):
        from semantic_os.backend.tests.test_widget import WidgetTests
        self.fixture=WidgetTests('test_origin_cors_and_iframe_policy');self.fixture.setUp()

    def tearDown(self):self.fixture.tearDown()

    def test_ontelyx_profile_and_voice_gate(self):
        from semantic_os.backend.assistant.widget import WidgetSettings,WidgetPublish
        fixture=self.fixture
        row=fixture.widget.get(fixture.actor,fixture.integration['id'])
        settings=WidgetSettings(**{**row['settings'],'appearance':'ontelyx-dark','color':'#54dde2'})
        fixture.widget.configure(fixture.actor,settings,row['id'])
        fixture.widget.publish(fixture.actor,row['id'],WidgetPublish(draft_id=fixture.draft['id'],confirmed=True))
        response=fixture.client.get('/widget/brand/'+fixture.public_id+'.css')
        self.assertEqual(response.status_code,200)
        self.assertIn('--surface:#080f1c',response.text)
        self.assertIn('--brand:#54dde2',response.text)
        self.assertNotIn('instructions',response.text)
        from semantic_os.backend.assistant.widget import Redeem
        ticket=fixture.widget.ticket(fixture.public_id,fixture.site)
        session=fixture.widget.redeem(fixture.public_id,Redeem(ticket=ticket['ticket'],parent_origin=fixture.site,locale='bg-BG'))
        self.assertFalse(session['voice_available'])
        self.assertEqual(fixture.client.post('/api/calls',headers={'Authorization':'Bearer '+session['session_token']}).status_code,401)

    def test_appearance_cannot_inject_css(self):
        from pydantic import ValidationError
        from semantic_os.backend.assistant.widget import WidgetSettings
        settings=self.fixture.integration['settings']
        with self.assertRaises(ValidationError):WidgetSettings(**{**settings,'appearance':'dark;}script{display:block'})
