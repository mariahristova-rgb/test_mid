import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet

ROOT=Path(__file__).resolve().parents[3]

class PublicStagingBootstrapTests(unittest.TestCase):
    def test_prepare_is_isolated_text_only_and_does_not_fake_domain_verification(self):
        sys.path.insert(0,str(ROOT/'semantic_os'))
        try:
            spec=importlib.util.spec_from_file_location('staging_bootstrap',ROOT/'semantic_os/deploy/phase15-staging/bootstrap.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            with patch.dict(os.environ,{'ASSISTANT_ENV':'staging','ASSISTANT_ALLOW_MOCK_BILLING':'true','WIDGET_PUBLIC_ORIGIN':module.WIDGET,'ASSISTANT_GOOGLE_LOGIN_ENABLED':'false'}),tempfile.TemporaryDirectory() as directory:
                store=module.Store();store.seed(module.TENANT,'offline-staging-owner')
                app=module.create_app(store=store,demo_enabled=False,encryption_key=Fernet.generate_key().decode())
                try:
                    approved=json.loads((ROOT/'semantic_os/config/ontelyx_concierge.json').read_text(encoding='utf-8'))
                    report=module.prepare(app,store,Path(directory),approved)
                    self.assertEqual(report['state'],'DOMAIN_VERIFICATION_REQUIRED')
                    widget=app.state.widget.get(store.principal('offline-staging-owner',module.TENANT),report['widget_id'])
                    self.assertNotEqual(widget['state'],'published')
                    self.assertFalse(widget['settings']['booking_enabled'])
                    assistant=store.get('assistants',module.TENANT,'default')
                    self.assertEqual(assistant['allowed_tools'],['EscalateToHuman'])
                    self.assertEqual(store.count('appointments',module.TENANT),0)
                    self.assertTrue((Path(directory)/'.well-known/testmid-widget'/ (report['public_id']+'.txt')).exists())
                    self.assertTrue((Path(directory)/'index.html').exists())
                    self.assertEqual(app.state.google.status(store.principal('offline-staging-owner',module.TENANT)),[])
                finally:app.state.voice_runtime.shutdown();store.close()
        finally:sys.path.pop(0)

if __name__=='__main__':unittest.main()
