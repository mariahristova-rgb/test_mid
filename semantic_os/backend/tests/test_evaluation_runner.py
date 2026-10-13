"""Evaluation integrity and redacted receipts, with no live providers."""
from copy import deepcopy
import json
import unittest
from types import SimpleNamespace
from scripts.evaluate_phase17 import validate_corpus,evaluate


class EvaluationRunnerTests(unittest.TestCase):
    def corpus(self):
        return {'version':'1.0.0','scope':'OFFLINE_CONTRACT_ONLY',
                'cases':[{'id':'synthetic','category':'security','test':'test_widget.WidgetTests.test_ticket_replay_expiry_and_wrong_parent'}],
                'unverified_layers':['LIVE_PROVIDER']}

    def test_invalid_empty_duplicate_and_nonoffline_corpus_fail_closed(self):
        mutations=[{'cases':[]},{'scope':'LIVE'},{'version':'invalid'},{'unverified_layers':[]},
                   {'cases':[self.corpus()['cases'][0]]*2},
                   {'cases':[{'id':'synthetic','category':'security','test':'outside.Class.test_send'}]},
                   {'cases':[{'id':'synthetic','category':'security','test':'test_widget.WidgetTests.setUp'}]}]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):validate_corpus({**self.corpus(),**mutation})
        with self.assertRaises(ValueError):validate_corpus({**self.corpus(),'unexpected':'private'})

    def test_failure_receipts_do_not_include_sensitive_assertion_payload(self):
        class Failure(unittest.TestCase):
            def runTest(self):self.fail('synthetic-sensitive-payload')
        loader=SimpleNamespace(loadTestsFromName=lambda _:unittest.TestSuite([Failure()]))
        rows=evaluate(self.corpus(),loader)
        self.assertEqual(rows[0]['status'],'FAIL')
        self.assertNotIn('synthetic-sensitive-payload',json.dumps(rows))
        self.assertIsNone(rows[0]['token_usage'])

    def test_skipped_missing_or_multiple_tests_cannot_pass(self):
        class Skip(unittest.TestCase):
            def runTest(self):self.skipTest('not tested')
        class Pass(unittest.TestCase):
            def runTest(self):pass
        for tests in ([],[Skip()],[Pass(),Pass()]):
            with self.subTest(count=len(tests)):
                rows=evaluate(self.corpus(),SimpleNamespace(loadTestsFromName=lambda _:unittest.TestSuite(tests)))
                self.assertEqual(rows[0]['status'],'FAIL')

    def test_valid_single_contract_pass_keeps_measurement_scope(self):
        class Pass(unittest.TestCase):
            def runTest(self):pass
        rows=evaluate(deepcopy(self.corpus()),SimpleNamespace(loadTestsFromName=lambda _:unittest.TestSuite([Pass()])))
        self.assertEqual(rows[0]['status'],'PASS')
        self.assertEqual(rows[0]['measurement_scope'],'SYNTHETIC_TEST_EXECUTION_INCLUDING_SETUP')
