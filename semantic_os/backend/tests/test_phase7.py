"""Deterministic integration contracts; not evidence of real model/audio/SIP journeys."""
from datetime import datetime, timezone
import json
import unittest
import httpx
from semantic_os.backend.assistant.domain import BookingIntent, DomainError, Incoming
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.providers import ProviderRegistry, MockLLMProvider
from semantic_os.backend.assistant.orchestration import Orchestrator
from semantic_os.backend.assistant.qwen import QwenSettings
from semantic_os.backend.assistant.voice import VoiceSessionManager


class RoutedQwenTests(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        self.store.seed('demo')
        self.store.seed('other', 'other-admin')
        self.actor = self.store.principal('demo-admin', 'demo')
        self.requests, self.mutate, self.bad = [], False, False
        self.providers = ProviderRegistry()
        self.providers.configure_qwen(QwenSettings(endpoint='https://owner.example/v1', max_context_tokens=8192),
            transport=httpx.MockTransport(self.handler))
        self.store.update('assistants', 'demo', 'default', {'llm_provider': 'qwen', 'llm_settings': {'model': 'Qwen3-4B', 'max_tokens': 256}})
        self.now = datetime(2030, 10, 8, 9, tzinfo=timezone.utc)
        self.orch = Orchestrator(self.store, self.providers, clock=lambda: self.now)

    def tearDown(self): self.store.close()

    def handler(self, request):
        body = json.loads(request.content)
        self.requests.append(body)
        if body.get('tools'):
            expected = json.loads(body['messages'][-1]['content'])
            arguments = expected['arguments']
            if self.mutate: arguments['duration_minutes'] = 480
            message = {'tool_calls': [{'id': 'synthetic-tool', 'function': {'name': expected['tool'], 'arguments': json.dumps(arguments)}}]}
        elif body.get('response_format'):
            content = body['messages'][-1]['content']
            if self.bad: message = {'content': 'invalid JSON'}
            else:
                from semantic_os.backend.assistant.domain import BookingInterpretationRequest
                parsed = MockLLMProvider().interpret_booking(BookingInterpretationRequest(content=content, locale='bg-BG'))
                message = {'content': parsed.model_dump_json()}
        else: message = {'content': 'Synthetic reply'}
        return httpx.Response(200, json={'model': 'Qwen3-4B', 'choices': [{'message': message}],
            'usage': {'prompt_tokens': 20, 'completion_tokens': 10}})

    def send(self, conversation, text, event, locale='bg-BG'):
        return self.orch.inbound(self.actor, conversation['id'], Incoming(content=text, event_id=event, locale=locale))

    def test_both_agents_bilingual_persistence_and_duplicates(self):
        for locale, request, name, confirm in (
            ('bg-BG', 'Искам да запиша час за утре в 15:00.', 'Казвам се Мария Иванова.', 'Потвърждавам'),
            ('en-US', 'Book an appointment tomorrow at 16:00', 'My name is Jane Example.', 'I confirm')):
            with self.subTest(locale=locale):
                conversation = self.orch.conversation(self.actor, 'default')
                result = self.send(conversation, request, locale+'1', locale)
                self.assertEqual(result['booking_status'], 'need_name')
                result = self.send(conversation, name, locale+'2', locale)
                self.assertEqual(result['booking_status'], 'awaiting_confirmation')
                before = self.store.count('appointments', 'demo')
                result = self.send(conversation, confirm, locale+'3', locale)
                self.assertEqual(result['booking_status'], 'completed')
                self.assertEqual(self.store.count('appointments', 'demo'), before+1)
                count = len(self.requests)
                self.assertTrue(self.send(conversation, confirm, locale+'3', locale)['duplicate'])
                self.assertEqual(len(self.requests), count)
                self.assertEqual(self.store.get('conversations', 'demo', conversation['id'])['active_locale'], locale)
        self.assertTrue(any(r.get('tools') for r in self.requests))
        receipts = [r for r in self.store.list('usage_records', 'demo') if r['kind'] == 'llm_inference']
        self.assertEqual(len(receipts), len(self.requests))
        self.assertEqual(self.store.count('appointments', 'other'), 0)

    def test_model_mutation_rolls_back_action_but_retains_observed_cost(self):
        conversation = self.orch.conversation(self.actor, 'default')
        self.mutate = True
        with self.assertRaises(DomainError): self.send(conversation, 'Book an appointment tomorrow at 15:00', 'mutated')
        self.assertEqual(self.store.count('appointments', 'demo'), 0)
        self.assertEqual(self.store.count('tool_executions', 'demo'), 0)
        self.assertEqual(len([r for r in self.store.list('usage_records', 'demo') if r['kind'] == 'llm_inference']), 2)

    def test_permissions_before_executor_inference_and_tenant_scope(self):
        self.store.update('assistants', 'demo', 'default', {'allowed_tools': []})
        conversation = self.orch.conversation(self.actor, 'default')
        with self.assertRaises(DomainError): self.send(conversation, 'Book an appointment tomorrow at 15:00', 'denied')
        self.assertFalse(any(r.get('tools') for r in self.requests))
        other = self.orch.conversation(self.store.principal('other-admin', 'other'), 'default')
        with self.assertRaises(DomainError): self.send(other, 'Hello', 'cross')

    def test_voice_handoff_id_and_explicit_switch_preserve_context(self):
        voice = VoiceSessionManager(self.store, self.providers, self.orch)
        call = voice.start(self.actor, 'default', 'bg-BG')
        call = voice.process_text(self.actor, call['id'], 'Искам да запиша час за утре в 15:00.', 'a')
        handoff = self.store.list('agent_executions', 'demo')[-1]['handoff']
        self.assertEqual(handoff['call_session_id'], call['id'])
        self.assertEqual(handoff['tenant_id'], 'demo')
        state = self.store.get('conversations', 'demo', call['conversation_id'])['booking_state']
        call = voice.process_text(self.actor, call['id'], 'Please continue in English.', 'switch')
        self.assertEqual(call['voice_locale'], 'en-US')
        self.assertEqual(self.store.get('conversations', 'demo', call['conversation_id'])['booking_state'], state)
        voice.finish(self.actor, call['id'])
        self.assertFalse(self.store.get('call_sessions', 'demo', call['id'])['stream_active'])

    def test_invalid_intent_usage_and_no_booking(self):
        self.bad = True
        conversation = self.orch.conversation(self.actor, 'default')
        with self.assertRaises(DomainError): self.send(conversation, 'Book tomorrow at 15:00', 'bad')
        self.assertEqual(self.store.count('appointments', 'demo'), 0)
        self.assertEqual(len([r for r in self.store.list('usage_records', 'demo') if r['kind'] == 'llm_inference']), 1)

    def test_api_activity_reads_persisted_booking_and_denies_other_tenant(self):
        from fastapi.testclient import TestClient
        from semantic_os.backend.assistant.api import create_app
        app = create_app(store=self.store, providers=self.providers, demo_enabled=True, demo_token='synthetic-phase7', clock=lambda:self.now)
        voice = app.state.voice
        call = voice.start(self.actor, 'default', 'bg-BG')
        for index, text in enumerate(('Искам да запиша час за утре в 15:00.', 'Казвам се Мария Иванова.', 'Потвърждавам')):
            voice.process_text(self.actor, call['id'], text, str(index))
        client = TestClient(app)
        headers = {'Authorization':'Bearer synthetic-phase7', 'X-Tenant-ID':'demo'}
        response = client.get('/api/calls/'+call['id']+'/activity', headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        activity = response.json()
        self.assertEqual(activity['appointments'][0]['id'], self.store.list('appointments','demo')[0]['id'])
        self.assertEqual(activity['appointments'][0]['status'], 'confirmed')
        self.assertTrue(activity['agents'])
        self.assertTrue(activity['tools'])
        self.assertTrue(activity['usage'])
        self.assertTrue(all(not row['content'] for row in activity['messages']))
        headers['X-Tenant-ID']='other'
        self.assertEqual(client.get('/api/calls/'+call['id']+'/activity',headers=headers).status_code,401)
        voice.finish(self.actor, call['id'])
        client.close(); app.state.voice_runtime.shutdown()

    def test_model_cancellation_rolls_back_inflight_booking(self):
        conversation = self.orch.conversation(self.actor,'default')
        original = self.handler
        def cancel(request):
            key = ('demo', conversation['id'])
            self.providers.cancel_llm('other', conversation['id'])
            self.assertFalse(self.providers.active_llms[key].cancelled.is_set())
            self.providers.cancel_llm(*key)
            return original(request)
        self.providers.qwen_transport=httpx.MockTransport(cancel)
        with self.assertRaises(DomainError) as error:
            self.send(conversation,'Book an appointment tomorrow at 15:00','cancelled')
        self.assertEqual(error.exception.code,'generation_cancelled')
        self.assertEqual(self.store.count('appointments','demo'),0)
        self.assertFalse(self.providers.active_llms)

    def test_next_monday_3pm_and_unavailable_alternatives(self):
        from semantic_os.backend.assistant.demo_seed import seed_smilecare, TENANT
        from semantic_os.backend.assistant.language import parse_date
        monday=datetime(2030,10,14,8,tzinfo=timezone.utc)
        self.assertEqual(parse_date('next Monday at 3 PM','en-US','Europe/Sofia',reference=monday).date().isoformat(),'2030-10-21')
        seed_smilecare(self.store,mode='mock',clock=lambda:self.now)
        actor=self.store.principal('smilecare-demo-admin',TENANT)
        conversation=self.orch.conversation(actor,'default')
        result=self.orch.inbound(actor,conversation['id'],Incoming(content='Hello, I would like to book a dental checkup next Monday at 3 PM.',event_id='next',locale='en-US'))
        self.assertEqual(result['booking_status'],'need_name')
        state=self.store.get('conversations',TENANT,conversation['id'])['booking_state']
        self.assertEqual(state['starts_at'],'2030-10-14T15:00:00+03:00')
        occupied=self.orch.conversation(actor,'default')
        result=self.orch.inbound(actor,occupied['id'],Incoming(content='Book an appointment next Monday at 14:00',event_id='occupied',locale='en-US'))
        self.assertEqual(result['booking_status'],'unavailable')
        self.assertTrue(result['outcome']['data']['available_slots'])
        self.assertIn('Available alternatives:',result['response'])

    def test_llm_entitlement_rejection_precedes_http_request(self):
        from semantic_os.backend.assistant.api import create_app
        app=create_app(store=self.store,providers=self.providers,demo_enabled=True,demo_token='synthetic-budget',clock=lambda:self.now)
        original=self.store.entitlements.check
        def check(tenant, category, quantity=1):
            if category=='llm_input_tokens': raise DomainError('upgrade_required',402)
            return original(tenant,category,quantity)
        self.store.entitlements.check=check
        conversation=self.orch.conversation(self.actor,'default')
        with self.assertRaises(DomainError) as error: self.send(conversation,'Book tomorrow at 15:00','quota')
        self.assertEqual(error.exception.code,'upgrade_required')
        self.assertEqual(self.requests,[])
        self.assertEqual(self.store.count('appointments','demo'),0)
        app.state.voice_runtime.shutdown()


if __name__ == '__main__': unittest.main()
