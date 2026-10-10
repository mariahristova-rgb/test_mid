"""CPU optimization safety contracts; these fixtures are not live speech evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import httpx
from semantic_os.backend.assistant.booking import explicit_confirmation
from semantic_os.backend.assistant.booking_grounding import explicit_entities
from semantic_os.backend.assistant.domain import BookingInterpretationRequest, DomainError
from semantic_os.backend.assistant.qwen import QwenProvider, QwenSettings
from semantic_os.backend.assistant.speech_integrity import verify_bgtts_cache


class CPUVoiceTests(unittest.TestCase):
    def provider(self, message):
        return QwenProvider(QwenSettings(endpoint='https://owner.example/v1',
            compact_intent=True, compact_tools=True), transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={'model':'Qwen3-4B',
                    'choices':[{'message':message}], 'usage':{'prompt_tokens':10,'completion_tokens':4}})))

    def test_compact_intent_preserves_clock_without_inventing_duration(self):
        for locale, text in [('bg-BG','Искам час за утре в 15:00.'),
                             ('en-US','Book tomorrow at 3 PM.')]:
            intent = self.provider({'content':'{"intent":"book"}'}).interpret_booking(
                BookingInterpretationRequest(content=text,locale=locale))
            self.assertIn('15:00', intent.date_text)
            self.assertIsNone(intent.duration_minutes)

    def test_tool_reference_is_exact_and_request_scoped(self):
        arguments = {'starts_at':'2030-10-14T15:00:00+03:00','duration_minutes':30}
        for name, value, valid in [('CheckAvailability', {'r':0}, True),
                                 ('CheckAvailability', {'r':False}, False),
                                 ('CheckAvailability', {'r':1}, False),
                                 ('CreateAppointment', {'r':0}, False)]:
            provider = self.provider({'tool_calls':[{'id':'fixture','function':
                {'name':name,'arguments':json.dumps(value)}}]})
            if valid:
                self.assertEqual(provider.propose_tool('CheckAvailability',arguments,{}), arguments)
            else:
                with self.assertRaises(DomainError):
                    provider.propose_tool('CheckAvailability',arguments,{})

    def test_confirmation_rejects_bad_asr_and_accepts_clear_bilingual_consent(self):
        for text in ('Купърх да вам.', 'ПОТМА САМАМ!', 'I might confirm', 'Do not confirm','I confirm?'):
            self.assertFalse(explicit_confirmation(text))
        for text in ('Да, потвърждавам часа за прегледа.', 'Yes, I confirm the appointment.','Да. Потвърждавам!','Yes. Confirm.'):
            self.assertTrue(explicit_confirmation(text))

    def test_spoken_clock_is_not_duration(self):
        entities = explicit_entities('Час за следващия понеделник в петнадесет часа.')
        self.assertEqual(entities['date_text'], 'следващия понеделник 15:00')
        self.assertIsNone(entities['duration_minutes'])
        self.assertEqual(explicit_entities('Book next Monday at 3 p.')['date_text'],'next monday 15:00')
        self.assertEqual(explicit_entities('Book tomorrow at 3:00 p.m.')['date_text'],'tomorrow 15:00')
        self.assertEqual(explicit_entities('Час за следващия понедельник в 15 часа.')['date_text'],'следващия понеделник 15:00')
        self.assertNotIn('contact_name',explicit_entities('Казом се Мария Демо',collecting_name=True))

    def test_speech_manifest_blocks_escape_and_missing_required_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'provenance.json').write_text(json.dumps({'models':[{
                'path':'../escape','size_bytes':1,'sha256':hashlib.sha256(b'x').hexdigest()}]}))
            (root/'wavlm-source.json').write_text('{}')
            with self.assertRaises(ValueError): verify_bgtts_cache(root)
            (root/'provenance.json').write_text('{"models":[]}')
            with self.assertRaises((ValueError, KeyError, FileNotFoundError)): verify_bgtts_cache(root)
