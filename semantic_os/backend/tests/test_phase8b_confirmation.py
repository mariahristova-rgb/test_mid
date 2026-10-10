"""Pending-context consent, durable single execution and diagnostic privacy."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from semantic_os.backend.assistant.domain import Incoming
from semantic_os.backend.assistant.observability import Operations, correlation_id
from semantic_os.backend.assistant.orchestration import Orchestrator
from semantic_os.backend.assistant.providers import ProviderRegistry
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.voice import VoiceSessionManager


class ConfirmationRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'confirmation.sqlite3'
        self.store = Store(str(self.path)); self.store.seed('demo')
        self.store.operations = Operations()
        self.actor = self.store.principal('demo-admin', 'demo')
        self.providers = ProviderRegistry()
        self.now = datetime(2030, 10, 8, 9, tzinfo=timezone.utc)
        self.orch = Orchestrator(self.store, self.providers, clock=lambda: self.now)
        self.conv = self.orch.conversation(self.actor, 'default', channel='voice')
        self.store.update('conversations', 'demo', self.conv['id'], {'call_session_id': 'fixture-call'})
        self.send('Здравейте, искам час за утре в 15:00.', 'date')
        self.send('Казвам се Мария Иванова.', 'name')
        self.pending = self.store.get('conversations', 'demo', self.conv['id'])['booking_state']
        self.assertEqual(self.pending['status'], 'awaiting_confirmation')

    def tearDown(self):
        self.store.close(); self.directory.cleanup()

    def send(self, text, event, locale='bg-BG'):
        token = correlation_id.set('synthetic-confirmation-correlation')
        try:
            return self.orch.inbound(self.actor, self.conv['id'], Incoming(content=text, event_id=event, locale=locale))
        finally:
            correlation_id.reset(token)

    def test_literal_pending_confirmation_skips_model_veto_and_persists_once(self):
        def fail(_): raise AssertionError('Literal pending consent must not call probabilistic intent')
        self.providers.llm.interpret_booking = fail
        result = self.send('Да, потвърждавам', 'confirmation')
        self.assertEqual(result['booking_status'], 'completed')
        self.assertTrue(self.send('Да, потвърждавам', 'confirmation')['duplicate'])
        self.assertEqual(self.send('Да', 'another-confirmation')['booking_status'], 'completed')
        executions = [r for r in self.store.list('tool_executions', 'demo') if r['tool'] == 'CreateAppointment']
        self.assertEqual(len(executions), 1)
        self.assertEqual(self.store.count('appointments', 'demo'), 1)
        trace = self.store.operations.snapshot('demo')['voice_trace']
        self.assertIn('appointment_persisted', [r['stage'] for r in trace])
        self.assertNotIn('Мария', json.dumps(trace, ensure_ascii=False))
        self.store.close(); self.store = Store(str(self.path))
        self.assertEqual(self.store.count('appointments', 'demo'), 1)
        self.assertEqual(self.store.get('conversations', 'demo', self.conv['id'])['booking_state']['status'], 'completed')

    def test_clear_rejection_does_not_book(self):
        result = self.send('Не, благодаря', 'reject')
        self.assertEqual(result['booking_status'], 'cancelled')
        self.assertEqual(self.store.count('appointments', 'demo'), 0)
        self.assertEqual(self.store.get('approvals', 'demo', self.pending['approval_id'])['status'], 'cancelled')

    def test_ambiguity_and_questions_keep_same_pending_proposal(self):
        for index, text in enumerate(('Може би', 'Да?', 'Не потвърждавам ли?', 'Путвърждавам часа')):
            result = self.send(text, 'unclear-' + str(index))
            self.assertEqual(result['booking_status'], 'awaiting_confirmation')
            state = self.store.get('conversations', 'demo', self.conv['id'])['booking_state']
            self.assertEqual(state['approval_id'], self.pending['approval_id'])
            self.assertEqual(self.store.count('appointments', 'demo'), 0)

    def test_expiry_prevents_booking(self):
        self.now += timedelta(minutes=16)
        result = self.send('Да', 'expired-confirmation')
        self.assertEqual(result['booking_status'], 'cancelled')
        self.assertEqual(self.store.count('appointments', 'demo'), 0)

    def test_requested_change_invalidates_old_approval(self):
        result = self.send('Искам друг час', 'change')
        self.assertEqual(result['booking_status'], 'need_date')
        self.assertEqual(self.store.get('approvals', 'demo', self.pending['approval_id'])['status'], 'cancelled')
        self.assertEqual(self.store.count('appointments', 'demo'), 0)

    def test_locale_switch_keeps_proposal_and_confirms_in_english(self):
        self.send('Please continue in English', 'switch', 'en-US')
        state = self.store.get('conversations', 'demo', self.conv['id'])['booking_state']
        self.assertEqual(state['approval_id'], self.pending['approval_id'])
        result = self.send('Yes', 'english-confirmation', 'en-US')
        self.assertEqual(result['booking_status'], 'completed')
        self.assertEqual(result['locale'], 'en-US')

    def test_trace_is_tenant_scoped_bounded_and_disallows_content(self):
        ops = Operations()
        with self.assertRaises(ValueError): ops.trace_voice('demo', 'stt_final', 'id', text='customer text')
        for _ in range(300): ops.trace_voice('demo', 'stt_final', 'id', transcript_present=True)
        self.assertEqual(len(ops.snapshot('demo')['voice_trace']), 256)
        self.assertEqual(ops.snapshot('other')['voice_trace'], [])

    def test_disconnect_cancels_pending_without_touching_completed_bookings(self):
        manager = VoiceSessionManager(self.store, self.providers, self.orch)
        call = self.store.add('call_sessions','demo', {'conversation_id':self.conv['id'],
            'assistant_id':'default','status':'listening','voice_locale':'bg-BG',
            'started_at':self.now.isoformat(),'provider':'mock','events':[]})
        manager.finish(self.actor, call['id'])
        self.assertEqual(self.store.get('approvals','demo',self.pending['approval_id'])['status'],'cancelled')
        self.assertEqual(self.store.get('conversations','demo',self.conv['id'])['booking_state']['status'],'cancelled')
        self.assertEqual(self.store.count('appointments','demo'),0)

    def test_rolled_back_write_is_not_traced_as_persisted(self):
        with self.assertRaises(RuntimeError):
            with self.store.transaction():
                self.send('Да', 'rolled-back-confirmation')
                raise RuntimeError('Synthetic outer transaction rollback')
        self.assertEqual(self.store.count('appointments','demo'),0)
        self.assertNotIn('appointment_persisted',[r['stage'] for r in self.store.operations.snapshot('demo')['voice_trace']])
