"""Optional keypad guard: ASR is never a write grant and tones bind to an armed proposal."""
from datetime import datetime,timedelta,timezone
import unittest
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.providers import ProviderRegistry
from semantic_os.backend.assistant.orchestration import Orchestrator
from semantic_os.backend.assistant.voice import VoiceSessionManager
from semantic_os.backend.assistant.domain import KeypadInput,DomainError
from semantic_os.backend.assistant.asterisk import ARIBridge,ARISettings
from semantic_os.backend.assistant.rtp import RTPAudioTransport
from types import SimpleNamespace
import httpx


class KeypadConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.store=Store();self.store.seed('demo')
        self.actor=self.store.principal('demo-admin','demo');self.providers=ProviderRegistry()
        self.now=datetime(2030,10,8,9,tzinfo=timezone.utc)
        self.orch=Orchestrator(self.store,self.providers,clock=lambda:self.now)
        settings=self.store.get('assistants','demo','default')['voice_settings']
        self.store.update('assistants','demo','default',{'voice_settings':{**settings,'booking_confirmation_mode':'keypad'}})
        self.voice=VoiceSessionManager(self.store,self.providers,self.orch)
        self.call=self.voice.start(self.actor,'default','bg-BG')
        self.voice.process_text(self.actor,self.call['id'],'Искам час за утре в 15:00.','date')
        self.voice.process_text(self.actor,self.call['id'],'Казвам се Мария Демо.','name')

    def tearDown(self):self.store.close()

    def tone(self,digit='1',event='key1',received=None):
        return self.voice.process_keypad(self.actor,self.call['id'],KeypadInput(digit=digit,utterance_id=event,received_at=received or self.now))

    def test_asr_affirmative_and_question_loss_never_book(self):
        for index,text in enumerate(('Да','Да, потвърждавам.','Да, потвърждавам?','Може би','Не потвърждавам ли?')):
            self.voice.process_text(self.actor,self.call['id'],text,'speech-'+str(index))
            self.assertEqual(self.store.count('appointments','demo'),0)
            self.assertEqual(self.store.get('conversations','demo',self.call['conversation_id'])['booking_state']['status'],'awaiting_confirmation')

    def test_early_tone_does_not_book(self):
        self.assertTrue(self.tone()['ignored_utterance'])
        before=self.now;self.now+=timedelta(seconds=1)
        self.assertTrue(self.voice.arm_keypad(self.actor,self.call['id']))
        self.assertTrue(self.tone(event='queued-early',received=before)['ignored_utterance'])
        self.assertEqual(self.store.count('appointments','demo'),0)

    def test_armed_tone_books_once_and_replay_is_safe(self):
        self.assertTrue(self.voice.arm_keypad(self.actor,self.call['id']))
        result=self.tone();self.assertIn('Часът е потвърден',result['last_response'])
        self.assertTrue(self.tone()['duplicate'])
        self.assertTrue(self.tone(event='second-press')['ignored_utterance'])
        self.assertEqual(self.store.count('appointments','demo'),1)
        self.assertEqual(len([t for t in self.store.list('tool_executions','demo') if t['tool']=='CreateAppointment']),1)
        self.assertTrue(all(not m['content'] for m in self.store.list('messages','demo',self.call['conversation_id'])))

    def test_changed_proposal_invalidates_armed_tone(self):
        self.voice.arm_keypad(self.actor,self.call['id'])
        self.voice.process_text(self.actor,self.call['id'],'Утре в 16:00','changed')
        self.assertTrue(self.tone()['ignored_utterance'])
        self.assertEqual(self.store.count('appointments','demo'),0)

    def test_zero_rejects_without_booking(self):
        self.tone('0','cancel')
        self.assertEqual(self.store.count('appointments','demo'),0)
        self.assertEqual(self.store.get('conversations','demo',self.call['conversation_id'])['booking_state']['status'],'cancelled')

    def test_revoked_permission_is_rechecked(self):
        self.voice.arm_keypad(self.actor,self.call['id'])
        self.store.update('assistants','demo','default',{'allowed_tools':['CheckAvailability']})
        with self.assertRaises(DomainError):self.tone()
        self.assertEqual(self.store.count('appointments','demo'),0)

    def test_hangup_prevents_late_tone(self):
        self.voice.arm_keypad(self.actor,self.call['id']);self.voice.finish(self.actor,self.call['id'])
        with self.assertRaises(DomainError):self.tone()
        self.assertEqual(self.store.count('appointments','demo'),0)

    def test_expiry_does_not_book(self):
        self.voice.arm_keypad(self.actor,self.call['id']);self.now+=timedelta(minutes=16)
        with self.assertRaises(DomainError):self.tone()
        self.assertEqual(self.store.count('appointments','demo'),0)

    def test_language_switch_repeats_proposal_and_preserves_context(self):
        before=self.store.get('conversations','demo',self.call['conversation_id'])['booking_state']['approval_id']
        result=self.voice.process_text(self.actor,self.call['id'],'Please continue in English','switch')
        self.assertEqual(result['voice_locale'],'en-US');self.assertIn('Press 1',result['last_response'])
        self.assertEqual(self.store.get('conversations','demo',self.call['conversation_id'])['booking_state']['approval_id'],before)
        self.assertTrue(self.voice.arm_keypad(self.actor,self.call['id']))
        self.tone()
        self.assertEqual(self.store.list('appointments','demo')[0]['locale'],'en-US')


class KeypadChannelTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_bound_accepted_channel_tones_are_queued(self):
        settings=ARISettings('http://127.0.0.1:8088/ari','fixture','x'*32,'demo','default','demo-admin','127.0.0.1','127.0.0.1')
        now=datetime(2030,10,8,9,tzinfo=timezone.utc)
        manager=SimpleNamespace(clock=lambda:now)
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda _:self.fail('No network call required')))
        bridge=ARIBridge(settings,manager,None,client=client)
        transport=RTPAudioTransport();transport.keypad_mode=True
        bridge.sessions['accepted']=transport;bridge.call_ids['accepted']='owned-call'
        template={'type':'ChannelDtmfReceived','application':settings.application,'channel':{'id':'accepted'},'digit':'1','duration_ms':150,'timestamp':'2030-10-08T09:00:00Z'}
        try:
            for replacement in ({'channel':{'id':'other'}},{'application':'other'},{'digit':'9'},{'duration_ms':True},{'timestamp':''}):
                await bridge.event({**template,**replacement})
            self.assertTrue(transport.queue.empty())
            await bridge.event(template)
            event=transport.queue.get_nowait()
            self.assertEqual(event['digit'],'1');self.assertEqual(event['received_at'],now.isoformat())
            self.assertTrue(event['utterance_id'].startswith('dtmf:'))
            transport.keypad_mode=False
            await bridge.event(template);self.assertTrue(transport.queue.empty())
        finally:await client.aclose()
