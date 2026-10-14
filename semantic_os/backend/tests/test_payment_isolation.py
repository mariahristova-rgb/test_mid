"""Production must never inherit payment simulation from local flags."""
import os
import unittest
from unittest.mock import patch
from datetime import datetime,timezone
from cryptography.fernet import Fernet
from semantic_os.backend.assistant.billing import BillingService
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.security import TenantSecretStore
from semantic_os.backend.assistant.domain import DomainError

class PaymentIsolation(unittest.TestCase):
    def test_production_flags_cannot_enable_mock_payment(self):
        for environment in ('production','staging'):
            with self.subTest(environment=environment),patch.dict(os.environ,{'ASSISTANT_ENV':environment,'ASSISTANT_ALLOW_MOCK_BILLING':'true'}):
                store=Store();store.seed()
                try:
                    service=BillingService(store,TenantSecretStore(store,Fernet.generate_key().decode()),lambda:datetime.now(timezone.utc),demo=True)
                    self.assertFalse(service.mock_enabled)
                    actor=store.principal('demo-admin','demo')
                    with self.assertRaises(DomainError):service.mock_pay(actor,'nonexistent','synthetic-event')
                    self.assertEqual(store.list('payment_events','demo'),[])
                finally:store.close()
