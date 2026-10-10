"""Explicit isolated staging rehearsal. Synthetic JWT issuer, mock providers, no live enablement."""
import os
from pathlib import Path
from types import SimpleNamespace
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from ..api.auth0_auth import Auth0Verifier
from .api import create_app
from .saas_domain import SubscriptionPlan
from .store import Store

if os.getenv('ASSISTANT_ENV') != 'staging' or os.getenv('ASSISTANT_STAGING_FIXTURE') != 'true':
    raise RuntimeError('This fixture may run only in explicitly enabled isolated staging.')
if any(os.getenv(k) == 'true' for k in ('ASSISTANT_ENABLE_LIVE_VOICE', 'ASSISTANT_ENABLE_LIVE_MESSAGING')):
    raise RuntimeError('Staging fixtures cannot enable live delivery.')

public_key = load_pem_public_key(Path(os.environ['ASSISTANT_STAGING_PUBLIC_KEY_FILE']).read_bytes())
class FixtureJWKS:
    def get_signing_key_from_jwt(self, token): return SimpleNamespace(key=public_key)

store = Store(os.environ['ASSISTANT_DATABASE'])
store.seed('staging', 'staging-owner')
app = create_app(store=store, demo_enabled=False, verifier=Auth0Verifier('identity.staging.example.invalid', 'staging-api', jwks=FixtureJWKS()),
    platform_subjects={'staging-owner'})
billing = app.state.billing
if not any(p['id'] == 'staging-fixture' for p in billing.plans()):
    billing.save_plan(SubscriptionPlan(id='staging-fixture', name_bg='Локален тестов план', name_en='Local staging fixture', trial_days=30,
        limits={'ai_messages': {'maximum': 10000}, 'tool_executions': {'maximum': 10000}, 'voice_seconds': {'maximum': 36000}}))
tenant = store.tenant('staging')
if not billing.entitlements.subscription('staging'):
    tenant.update(email_verified=True, onboarding_state='configuring', owner_subject='staging-owner', administrator_email='owner@example.invalid')
    store.update_tenant('staging', tenant)
    if not store.find('billing_customers', 'staging', 'current'):
        store.add('billing_customers', 'staging', billing.provider.create_customer('staging'), external_key='current')
    billing.select_trial(store.principal('staging-owner', 'staging'), 'staging-fixture', 'monthly')
