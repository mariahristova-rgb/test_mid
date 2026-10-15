from datetime import datetime,timedelta,timezone
from hashlib import sha256
import unittest
from semantic_os.backend.assistant.external_acceptance import authorize_acceptance
from semantic_os.backend.assistant.domain import DomainError


class ExternalAcceptanceTests(unittest.TestCase):
    def test_gpu_default_runs_no_inference_and_execution_requires_approval(self):
        from scripts.phase26c_qwen_benchmark import benchmark
        from unittest.mock import patch
        report=benchmark()
        self.assertEqual(report['gpu_performance'],'NOT_MEASURED')
        self.assertEqual(report['samples'],[])
        self.assertEqual(report['capacity_assumptions'][-1]['responses_per_day'],30000)
        with patch.dict('os.environ',{'PHASE26C_GPU_BENCHMARK_APPROVED':'false'}):
            with self.assertRaises(RuntimeError):benchmark(execute=True)

    def test_inference_tenant_and_global_admission_release_after_error(self):
        from semantic_os.backend.assistant.providers import ProviderRegistry
        from semantic_os.backend.assistant.qwen import QwenSettings
        from semantic_os.backend.assistant.store import Store
        registry=ProviderRegistry(llm_global_limit=1,llm_tenant_limit=1)
        registry.configure_qwen(QwenSettings(endpoint='https://synthetic.example.invalid/v1'),secret='synthetic-only')
        store=Store();self.addCleanup(store.close);store.seed('one','admin');store.seed('two','admin')
        assistant={**store.get('assistants','one','default'),'llm_provider':'qwen','llm_settings':{'model':'Qwen3-4B'}}
        conversation={'id':'synthetic-a','active_locale':'en-US','channel':'web_chat'}
        one=store.principal('admin','one');two=store.principal('admin','two')
        with self.assertRaises(RuntimeError):
            with registry.llm_session(assistant,conversation,one,store,'synthetic'):
                for actor in (one,two):
                    with self.assertRaises(DomainError) as error:
                        with registry.llm_session(assistant,{**conversation,'id':'other'},actor,store,'synthetic'):pass
                    self.assertEqual(error.exception.status,429)
                raise RuntimeError('synthetic cancellation')
        self.assertEqual(registry.active_llms,{})

    def test_default_disabled_expiry_account_resource_and_action_boundaries(self):
        current=datetime(2026,10,15,10,tzinfo=timezone.utc)
        manifest={'approval_id':'synthetic-approval','provider':'google','tenant_id':'synthetic',
            'account_sha256':sha256(b'synthetic-account').hexdigest(),'resource_sha256':sha256(b'synthetic-calendar').hexdigest(),
            'approved_at':current.isoformat(),'expires_at':(current+timedelta(minutes=30)).isoformat(),
            'isolated_test_calendar':True,'consent_receipt':True,'actions':['read'],'max_events':1,'send_updates':'none','cleanup_approved':True}
        options={'approval_id':'synthetic-approval','tenant':'synthetic','account':'synthetic-account','resource':'synthetic-calendar','action':'read','clock':lambda:current}
        with self.assertRaises(DomainError):authorize_acceptance(manifest,**options)
        self.assertEqual(authorize_acceptance(manifest,enabled=True,**options)['max_events'],1)
        for changed in ({'tenant':'other'},{'account':'other'},{'resource':'other'},{'action':'create_one_test'},{'clock':lambda:current+timedelta(hours=1)}):
            with self.assertRaises(DomainError):authorize_acceptance(manifest,enabled=True,**{**options,**changed})
