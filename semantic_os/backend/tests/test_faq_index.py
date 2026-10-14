import unittest
from semantic_os.backend.assistant.faq_index import lookup

class FAQIndexTests(unittest.TestCase):
    def test_index_provenance_locale_and_configuration_changes(self):
        entry={'question_bg':'Въпрос','question_en':'Question','answer_bg':'Отговор','answer_en':'Answer'}
        first=lookup([entry],' QUESTION ','bg-BG')
        self.assertEqual(first['answer'],'Отговор');self.assertEqual(first['provenance']['locale'],'bg-BG')
        changed=lookup([{**entry,'answer_bg':'Нов отговор'}],'Въпрос','bg-BG')
        self.assertNotEqual(first['provenance']['sha256'],changed['provenance']['sha256'])
        self.assertIsNone(lookup([],'Question','en-US'))
        self.assertIsNone(lookup([entry],'unsupported','en-US'))
        self.assertNotIn('Answer',str(first['provenance']))
