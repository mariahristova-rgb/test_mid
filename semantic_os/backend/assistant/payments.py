"""Local hosted-checkout contract. No card data, network requests or real charges."""
import hashlib
import hmac
import json
from pydantic import ValidationError
from .domain import DomainError
from .saas_domain import PaymentEvent


class MockPaymentProvider:
    state = 'MOCK'

    def create_customer(self, tenant_id): return {'external_customer_id': 'mock-customer:' + tenant_id, 'provider': 'mock'}
    def create_checkout(self, invoice, key):
        return {'checkout_id': 'mock-checkout:' + invoice['id'], 'checkout_url': None,
            'hosted_checkout_status': 'local_fixture', 'state': 'MOCK', 'idempotency_key': key}
    def create_subscription(self, customer, plan, interval):
        return {'external_subscription_id': 'mock-subscription:' + customer['external_customer_id'], 'provider': 'mock'}
    def update_subscription(self, subscription, changes): return {**subscription, **changes}
    def cancel_subscription(self, subscription): return {'cancel_at_period_end': True, 'provider': 'mock'}
    def retrieve_invoice(self, invoice): return invoice
    def payment_status(self, invoice): return invoice['status']
    def verify_webhook(self, raw, signature, secret):
        expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        if not secret or not hmac.compare_digest(signature, expected): raise DomainError('invalid_signature', 401)
        try: return PaymentEvent.model_validate(json.loads(raw))
        except (ValidationError, ValueError, TypeError): raise DomainError('invalid_input', 422) from None
