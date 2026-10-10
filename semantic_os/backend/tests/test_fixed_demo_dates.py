"""Ground explicit spoken day/month/year forms without model date guessing."""
from datetime import datetime,timezone
import unittest
from semantic_os.backend.assistant.booking_grounding import explicit_entities
from semantic_os.backend.assistant.language import parse_date
from semantic_os.backend.assistant.domain import DomainError


class FixedDemoDateTests(unittest.TestCase):
    def test_bulgarian_and_english_explicit_months(self):
        for phrase,locale,hour in [('Искам час на 13 октомври 2026 в петнадесет часа.','bg-BG',15),
                                  ('Book October 13, 2026 at 4 PM.','en-US',16),
                                  ('Book 13th October 2026 at 17:00.','en-US',17)]:
            entity=explicit_entities(phrase)['date_text']
            result=parse_date(entity,locale,'Europe/Sofia',reference=datetime(2026,10,10,tzinfo=timezone.utc))
            self.assertEqual(result.isoformat(),f'2026-10-13T{hour:02d}:00:00+03:00')

    def test_full_iso_keeps_explicit_offset(self):
        self.assertEqual(explicit_entities('Book 2026-10-13T15:00:00+03:00')['date_text'],'2026-10-13T15:00:00+03:00')

    def test_missing_year_does_not_create_absolute_date(self):
        self.assertEqual(explicit_entities('Book October 13 at 15:00')['date_text'],'15:00')

    def test_invalid_explicit_calendar_date_requires_clarification(self):
        entity=explicit_entities('Book 31 February 2026 at 15:00')['date_text']
        with self.assertRaises(DomainError):parse_date(entity,'en-US','Europe/Sofia')
