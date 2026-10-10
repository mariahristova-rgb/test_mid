"""Recovery safety contracts; fixtures do not establish live speech acceptance."""
import base64
import struct
import unittest
from semantic_os.backend.assistant.audio import TurnBuffer
from semantic_os.backend.assistant.domain import AudioFrame
from semantic_os.backend.assistant.booking import explicit_confirmation,explicit_cancellation
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.providers import ProviderRegistry
from semantic_os.backend.assistant.orchestration import Orchestrator
from semantic_os.backend.assistant.domain import Incoming,BookingIntent
from datetime import datetime,timezone


class Phase8VoiceTests(unittest.TestCase):
    def frame(self,sequence,amplitude):
        return AudioFrame(sequence=sequence,utterance_id='fixture',encoding='pcm16',sample_rate=8000,
            payload=base64.b64encode(struct.pack('<160h',*([amplitude]*160))).decode())

    def test_preroll_preserves_quiet_onset_and_emits_only_one_final(self):
        buffer=TurnBuffer(silence_ms=100,pre_roll_ms=200)
        for number in range(5): self.assertIsNone(buffer.feed(self.frame(number,100))[0])
        self.assertIsNone(buffer.feed(self.frame(5,1000))[0])
        item=None
        for number in range(6,11): item,_=buffer.feed(self.frame(number,0))
        self.assertIsNotNone(item)
        values=struct.unpack('<'+'h'*(len(item[0])//2),item[0])
        self.assertEqual(values[:800],tuple([100]*800))
        for number in range(11,100): self.assertIsNone(buffer.feed(self.frame(number,0))[0])
        self.assertLessEqual(len(buffer.pre_roll),3200)

    def test_required_confirmation_and_negative_question_corruption(self):
        self.assertTrue(explicit_confirmation('Да, потвърждавам резервацията.'))
        for phrase in ('Не потвърждавам резервацията.','Да, потвърждавам резервацията?','Де потвърждавам.','Путвърждавам часа.'):
            self.assertFalse(explicit_confirmation(phrase))

    def test_cancellation_requires_clear_caller_words(self):
        for phrase in ('Cancel booking','Please cancel the booking.','Не потвърждавам','Отказвам часа'):
            self.assertTrue(explicit_cancellation(phrase))
        for phrase in ('Do not cancel','Путвърждавам часа','Should I cancel?','Да, потвърждавам резервацията'):
            self.assertFalse(explicit_cancellation(phrase))

    def test_model_cancel_guess_preserves_pending_confirmation(self):
        store=Store(); store.seed('demo')
        try:
            actor=store.principal('demo-admin','demo'); providers=ProviderRegistry()
            orch=Orchestrator(store,providers,clock=lambda:datetime(2030,10,8,9,tzinfo=timezone.utc))
            conversation=orch.conversation(actor,'default')
            for event,text in [('date','Book tomorrow at 15:00'),('name','My name is Jane Smith')]:
                orch.inbound(actor,conversation['id'],Incoming(content=text,event_id=event,locale='en-US'))
            state=store.get('conversations','demo',conversation['id'])['booking_state']
            self.assertEqual(state['status'],'awaiting_confirmation')
            providers.llm.interpret_booking=lambda _:BookingIntent(intent='cancel')
            result=orch.inbound(actor,conversation['id'],Incoming(content='Путвърждавам часа',event_id='unclear',locale='bg-BG'))
            self.assertEqual(result['booking_status'],'awaiting_confirmation')
            self.assertEqual(store.get('approvals','demo',state['approval_id'])['status'],'pending')
            self.assertEqual(store.count('appointments','demo'),0)
        finally: store.close()
