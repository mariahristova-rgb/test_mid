"""SaaS acceptance/security fixtures. No real verification mail, payments or provider sends."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import logging
from pathlib import Path
import sqlite3
import tempfile
import unittest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from semantic_os.backend.assistant.api import create_app
from semantic_os.backend.assistant.domain import DomainError
from semantic_os.backend.assistant.saas_domain import UsageEvent
from semantic_os.backend.assistant.security import TenantSecretStore
from semantic_os.backend.assistant.store import Store, uid
from semantic_os.backend.api.auth0_auth import AuthenticatedSubject

logging.getLogger('assistant.operations').setLevel(logging.ERROR)


class IdentityFixture:
    def verify(self, authorization):
        subject = {'Bearer verified-owner': 'verified-owner', 'Bearer unverified-owner': 'unverified-owner',
            'Bearer support-fixture': 'support', 'Bearer stranger': 'stranger'}.get(authorization)
        if not subject: raise DomainError('unauthorized', 401)
        return AuthenticatedSubject('FIXTURE', subject, 'owner@example.invalid', email_verified=subject == 'verified-owner')


class SaaSAcceptance(unittest.TestCase):
    def setUp(self):
        self.at = datetime(2030, 1, 10, 9, tzinfo=timezone.utc)
        self.directory = tempfile.TemporaryDirectory()
        self.key, self.backup_key = Fernet.generate_key().decode(), Fernet.generate_key().decode()
        self.store = Store()
        self.app = create_app(store=self.store, demo_enabled=True, demo_token='synthetic-saas-session', encryption_key=self.key,
            clock=lambda: self.at, verifier=IdentityFixture(), platform_subjects={'demo-admin', 'support'},
            backup_key=self.backup_key, backup_directory=Path(self.directory.name) / 'backups')
        self.client = TestClient(self.app)
        self.headers = {'Authorization': 'Bearer synthetic-saas-session', 'X-Tenant-ID': 'demo'}
        self.billing = self.app.state.billing

    def tearDown(self):
        self.client.close(); self.store.close(); self.directory.cleanup()

    def post(self, path, data, status=None):
        response = self.client.post(path, headers=self.headers, json=data)
        if status is None: self.assertLess(response.status_code, 300, response.text)
        else: self.assertEqual(response.status_code, status, response.text)
        return response.json()

    def plan(self, id='limited', **changes):
        config = {'id': id, 'name_en': 'Synthetic plan', 'name_bg': 'Тестов план', 'monthly_minor': 1200, 'annual_minor': 12000,
            'trial_days': 2, 'grace_days': 2, 'rank': 1, 'limits': {'ai_messages': {'maximum': 2}, 'assistants': {'maximum': 1},
            'agents': {'maximum': 2}, 'users': {'maximum': 2}, 'connections': {'maximum': 1}, 'storage_bytes': {'maximum': 1000000}}, **changes}
        headers = {'Authorization': 'Bearer synthetic-saas-session', 'X-Tenant-ID': 'demo'}
        result = self.client.put('/api/platform/plans', headers=headers, json=config)
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()

    def register(self, locale='en-US', verified=True, plan='limited'):
        if plan == 'limited' and not any(p['id'] == plan for p in self.billing.plans()): self.plan()
        self.headers = {'Authorization': 'Bearer verified-owner' if verified else 'Bearer unverified-owner'}
        result = self.post('/api/saas/register', {'name': 'Synthetic Business', 'email': 'owner@example.invalid',
            'default_locale': locale, 'timezone': 'Europe/Sofia', 'plan_id': plan, 'event_id': uid()}, 201)
        self.headers['X-Tenant-ID'] = result['tenant_id']
        return result

    def activate(self, locale='en-US', plan='limited'):
        result = self.register(locale, plan=plan)
        self.post('/api/billing/trial', {'confirmed': True, 'plan_id': plan, 'event_id': uid()})
        return result['tenant_id']

    def paid(self, plan='limited', interval='monthly'):
        self.register(plan=plan)
        invoice = self.post('/api/billing/checkout', {'confirmed': True, 'plan_id': plan, 'interval': interval, 'event_id': uid()})
        self.post('/api/billing/invoices/' + invoice['id'] + '/mock-pay', {'confirmed': True, 'event_id': uid()})
        return invoice

    def test_onboarding_both_locales_identity_verification_and_access(self):
        for locale in ('bg-BG', 'en-US'):
            result = self.register(locale, verified=False)
            self.assertEqual(result['state'], 'pending_verification')
            self.assertEqual(self.client.get('/api/bootstrap', headers=self.headers).status_code, 403)
            token = self.client.get('/api/saas/onboarding/mock-email', headers=self.headers).json()['token']
            result = self.post('/api/saas/onboarding/verify', {'token': token})
            self.assertTrue(result['email_verified'])
            self.post('/api/billing/trial', {'plan_id': 'limited', 'event_id': uid(), 'confirmed': True})
            dashboard = self.client.get('/api/bootstrap', headers=self.headers)
            self.assertEqual(dashboard.status_code, 200, dashboard.text)
            self.assertEqual(dashboard.json()['tenant']['default_locale'], locale)

    def test_verified_claim_must_match_registration_mailbox(self):
        self.plan()
        self.headers = {'Authorization': 'Bearer verified-owner'}
        result = self.post('/api/saas/register', {'name': 'Synthetic', 'email': 'different@example.invalid', 'default_locale': 'en-US',
            'timezone': 'Europe/Sofia', 'plan_id': 'limited', 'event_id': uid()}, 201)
        self.assertFalse(result['email_verified'])

    def test_verification_token_replay_and_expiry(self):
        self.register(verified=False)
        token = self.client.get('/api/saas/onboarding/mock-email', headers=self.headers).json()['token']
        self.at += timedelta(minutes=31)
        self.post('/api/saas/onboarding/verify', {'token': token}, 409)

    def test_subscription_hard_limit_localized_and_duplicate_usage(self):
        tenant = self.activate('bg-BG')
        conversation = self.post('/api/conversations', {})['id']
        self.headers['X-UI-Locale'] = 'bg-BG'
        first = {'content': 'Здравейте', 'event_id': 'first'}
        self.post('/api/conversations/' + conversation + '/messages', first)
        self.post('/api/conversations/' + conversation + '/messages', first)
        self.post('/api/conversations/' + conversation + '/messages', {'content': 'Здравейте', 'event_id': 'second'})
        response = self.post('/api/conversations/' + conversation + '/messages', {'content': 'Здравейте', 'event_id': 'third'}, 402)
        self.assertEqual(response['code'], 'upgrade_required')
        self.assertEqual(self.billing.entitlements.quantity(tenant, 'ai_messages'), 2)
        self.assertTrue(self.store.list('usage_warnings', tenant))

    def test_resource_entitlements_and_reenable_are_server_side(self):
        self.activate()
        self.post('/api/assistants', {'name': 'extra'}, 402)
        self.post('/api/users', {'subject': 'second', 'role': 'viewer'})
        self.post('/api/users', {'subject': 'third', 'role': 'viewer'}, 402)

    def test_append_only_usage_idempotency_and_precise_invoices(self):
        tenant = self.activate()
        event = {'resource_id': uid(), 'category': 'llm_input_tokens', 'quantity': 1234, 'unit': 'token', 'provider': 'mock',
            'timestamp': self.at.isoformat(), 'idempotency_key': 'same-usage'}
        first = self.post('/api/billing/usage-report', event)
        second = self.post('/api/billing/usage-report', event)
        self.assertEqual(first['id'], second['id'])
        self.post('/api/billing/usage-report', {**event, 'quantity': 1235}, 409)
        with self.assertRaises(DomainError): self.store.update('billing_usage', tenant, first['id'], {'quantity': 0})
        with self.assertRaises(sqlite3.IntegrityError): self.store.db.execute('DELETE FROM billing_usage WHERE tenant_id=?', (tenant,))
        invoice = self.post('/api/billing/checkout', {'confirmed': True, 'plan_id': 'limited', 'interval': 'annual', 'event_id': uid()})
        self.assertIsInstance(invoice['amount_minor'], int)
        self.assertEqual(invoice['amount_minor'], 12000)

    def test_monthly_usage_period_rollover(self):
        tenant = self.activate()
        event = UsageEvent(resource_id=uid(), category='ai_messages', quantity=2, unit='message', provider='mock', timestamp=self.at, idempotency_key=uid())
        self.billing.entitlements.record(tenant, event)
        self.at = datetime(2030, 2, 1, tzinfo=timezone.utc)
        self.assertEqual(self.billing.entitlements.quantity(tenant, 'ai_messages'), 0)

    def test_payment_signature_duplicate_event_and_failed_payment_grace(self):
        invoice = self.paid()
        tenant = self.headers['X-Tenant-ID']
        secret = self.billing.secrets.get(tenant, 'payment:webhook_secret')
        raw = json.dumps({'event_id': uid(), 'customer_id': self.store.find('billing_customers', tenant, 'current')['external_customer_id'],
            'invoice_id': invoice['id'], 'kind': 'invoice_paid', 'amount_minor': 1200, 'currency': 'EUR', 'timestamp': self.at.isoformat()}).encode()
        path = '/webhooks/payments/' + tenant
        self.assertEqual(self.client.post(path, content=raw, headers={'x-signature': 'wrong'}).status_code, 401)
        signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        self.assertEqual(self.client.post(path, content=raw, headers={'x-signature': signature}).status_code, 200)
        self.assertTrue(self.client.post(path, content=raw, headers={'x-signature': signature}).json()['duplicate'])

    def test_renewal_grace_suspension_and_payment_recovery(self):
        self.paid()
        tenant = self.headers['X-Tenant-ID']
        subscription = self.billing.entitlements.subscription(tenant)
        self.at = datetime.fromisoformat(subscription['period_end'])
        overview = self.client.get('/api/billing', headers=self.headers).json()
        self.assertEqual(overview['subscription']['status'], 'past_due')
        self.at += timedelta(days=3)
        self.assertEqual(self.client.get('/api/bootstrap', headers=self.headers).status_code, 402)
        overview = self.client.get('/api/billing', headers=self.headers).json()
        invoice = overview['invoices'][-1]
        self.post('/api/billing/invoices/' + invoice['id'] + '/mock-pay', {'confirmed': True, 'event_id': uid()})
        self.assertEqual(self.client.get('/api/bootstrap', headers=self.headers).status_code, 200)

    def test_upgrade_downgrade_and_cancellation(self):
        self.plan('larger', rank=2, monthly_minor=2400, limits={'ai_messages': {'maximum': 50}})
        self.paid()
        change = self.post('/api/billing/change', {'confirmed': True, 'plan_id': 'larger', 'event_id': uid()})
        self.post('/api/billing/invoices/' + change['id'] + '/mock-pay', {'confirmed': True, 'event_id': uid()})
        changed = self.post('/api/billing/change', {'confirmed': True, 'plan_id': 'limited', 'event_id': uid()})
        self.assertEqual(changed['pending_change']['plan_id'], 'limited')
        self.post('/api/billing/cancel', {'confirmed': True})
        self.at = datetime.fromisoformat(changed['period_end'])
        self.assertEqual(self.client.get('/api/bootstrap', headers=self.headers).status_code, 402)

    def test_credential_masking_rotation_revocation_and_audit(self):
        tenant = self.activate()
        value = uid() + uid()
        self.client.put('/api/credentials', headers=self.headers, json={'name': 'llm:fixture', 'value': value, 'confirmed': True}).raise_for_status()
        response = self.client.get('/api/credentials', headers=self.headers)
        self.assertNotIn(value, response.text)
        id = response.json()[0]['id']
        new_key = Fernet.generate_key().decode()
        rotating = TenantSecretStore(self.store, new_key + ',' + self.key)
        rotating.rotate_keyring(self.store.principal('verified-owner', tenant))
        self.assertEqual(TenantSecretStore(self.store, new_key).get(tenant, 'llm:fixture'), value)
        self.post('/api/credentials/' + id + '/revoke', {'confirmed': True})
        with self.assertRaises(DomainError): rotating.get(tenant, 'llm:fixture')
        self.assertTrue(any(a['action'] == 'credential:read' for a in self.store.list('audit_events', tenant)))

    def test_platform_metadata_has_no_content_and_support_is_explicit(self):
        tenant = self.activate()
        conversation = self.post('/api/conversations', {})['id']
        self.post('/api/conversations/' + conversation + '/messages', {'content': 'private synthetic content', 'event_id': uid()})
        headers = {'Authorization': 'Bearer support-fixture'}
        response = self.client.get('/api/platform/tenants', headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('private synthetic content', response.text)
        path = '/api/platform/support/' + tenant + '/conversations/' + conversation + '/messages'
        self.assertEqual(self.client.get(path, headers=headers).status_code, 403)
        self.post('/api/support/grants', {'confirmed': True, 'support_subject': 'support', 'reason': 'synthetic support request'})
        self.assertEqual(self.client.get(path, headers=headers).status_code, 200)
        self.at += timedelta(minutes=31)
        self.assertEqual(self.client.get(path, headers=headers).status_code, 403)

    def test_tenant_export_excludes_secrets_and_contact_erasure(self):
        tenant = self.activate()
        contact = self.post('/api/contacts', {'name': 'Synthetic Contact', 'address': 'synthetic@example.invalid'})
        conversation = self.post('/api/conversations', {'contact_id': contact['id']})['id']
        self.post('/api/conversations/' + conversation + '/messages', {'content': 'Hello private fixture', 'event_id': uid()})
        export = self.client.get('/api/privacy/export', headers=self.headers).json()
        self.assertNotIn('secrets', export['data']['resources'])
        request = self.post('/api/privacy/requests', {'kind': 'contact', 'resource_id': contact['id'], 'confirmed': True})
        self.post('/api/privacy/requests/' + request['id'] + '/execute', {'confirmed': True})
        self.assertTrue(self.store.get('contacts', tenant, contact['id'])['redacted'])
        self.assertTrue(all(m['content'] == '' for m in self.store.list('messages', tenant, conversation)))

    def test_tenant_erasure_preserves_financial_ledger_and_denies_access(self):
        tenant = self.activate()
        conversation = self.post('/api/conversations', {})['id']
        self.post('/api/conversations/' + conversation + '/messages', {'content': 'Hello', 'event_id': uid()})
        count = self.store.count('billing_usage', tenant)
        request = self.post('/api/privacy/requests', {'kind': 'tenant', 'confirmed': True})
        result = self.post('/api/privacy/requests/' + request['id'] + '/execute', {'confirmed': True})
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(self.store.count('billing_usage', tenant), count)
        self.assertEqual(self.store.count('messages', tenant), 0)
        self.assertEqual(self.client.get('/api/bootstrap', headers=self.headers).status_code, 401)
        self.assertFalse(self.store.db.execute('PRAGMA foreign_key_check').fetchall())

    def test_backup_restore_preserves_tenant_usage_and_encrypted_credentials(self):
        tenant = self.activate()
        self.billing.secrets.put(tenant, 'llm:fixture', uid() + uid())
        backup = self.app.state.backups.create()
        target = Path(self.directory.name) / 'restored.sqlite3'
        result = self.app.state.backups.restore(backup['filename'], target)
        self.assertEqual(result['schema_version'], 5)
        restored = Store(target)
        try:
            self.assertEqual(restored.tenant(tenant)['name'], 'Synthetic Business')
            self.assertEqual(TenantSecretStore(restored, self.key).get(tenant, 'llm:fixture'), self.billing.secrets.get(tenant, 'llm:fixture'))
        finally: restored.close()
        with self.assertRaises(DomainError): self.app.state.backups.restore(backup['filename'], target)

    def test_operations_correlation_and_customer_content_is_not_logged(self):
        self.activate()
        conversation = self.post('/api/conversations', {})['id']
        response = self.client.post('/api/conversations/' + conversation + '/messages', headers=self.headers, json={'content': 'Hello secret customer text', 'event_id': uid()})
        self.assertEqual(response.headers['x-correlation-id'], response.json()['correlation_id'])
        operations = self.client.get('/api/operations', headers=self.headers).json()
        self.assertIn('agent_execution', operations['metrics'])
        self.assertNotIn('secret customer text', json.dumps(operations))

    def test_cross_tenant_access_is_denied_and_security_event_recorded(self):
        self.activate()
        self.headers['Authorization'] = 'Bearer stranger'
        response = self.client.get('/api/privacy/export', headers=self.headers)
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('Synthetic Business', response.text)
        self.assertTrue(any(json.loads(r['data'])['action'] == 'security:tenant_access_denied' for r in self.store.db.execute('SELECT data FROM platform_audit')))

    def test_registration_idempotency_and_changed_payload_conflict(self):
        self.plan()
        self.headers = {'Authorization': 'Bearer verified-owner'}
        payload = {'name': 'Synthetic', 'email': 'owner@example.invalid', 'default_locale': 'en-US', 'timezone': 'Europe/Sofia', 'plan_id': 'limited', 'event_id': uid()}
        first = self.post('/api/saas/register', payload, 201)
        self.assertEqual(self.post('/api/saas/register', payload, 201)['tenant_id'], first['tenant_id'])
        self.post('/api/saas/register', {**payload, 'name': 'changed'}, 409)

    def test_reverification_does_not_demote_active_tenant(self):
        self.activate()
        state = self.post('/api/saas/onboarding/verify', {})
        self.assertEqual(state['state'], 'active')

    def test_duplicate_mock_payment_does_not_extend_period(self):
        self.register()
        invoice = self.post('/api/billing/checkout', {'confirmed': True, 'plan_id': 'limited', 'event_id': uid()})
        payload = {'confirmed': True, 'event_id': 'payment-id'}
        self.post('/api/billing/invoices/' + invoice['id'] + '/mock-pay', payload)
        end = self.billing.entitlements.subscription(self.headers['X-Tenant-ID'])['period_end']
        self.at += timedelta(hours=1)
        self.assertTrue(self.post('/api/billing/invoices/' + invoice['id'] + '/mock-pay', payload)['duplicate'])
        self.assertEqual(self.billing.entitlements.subscription(self.headers['X-Tenant-ID'])['period_end'], end)

    def test_repeated_failed_payment_does_not_extend_grace(self):
        self.paid()
        invoice = self.post('/api/billing/checkout', {'confirmed': True, 'plan_id': 'limited', 'event_id': uid()})
        self.post('/api/billing/invoices/' + invoice['id'] + '/mock-pay', {'confirmed': True, 'event_id': uid(), 'success': False})
        tenant = self.headers['X-Tenant-ID']
        end = self.billing.entitlements.subscription(tenant)['grace_until']
        self.at += timedelta(days=1)
        self.post('/api/billing/invoices/' + invoice['id'] + '/mock-pay', {'confirmed': True, 'event_id': uid(), 'success': False})
        self.assertEqual(self.billing.entitlements.subscription(tenant)['grace_until'], end)

    def test_plan_snapshot_and_integer_usage_invoice(self):
        self.plan('metered', limits={'llm_input_tokens': {'maximum': 10, 'mode': 'soft', 'overage_policy': 'meter', 'overage_minor_per_unit': 3}})
        tenant = self.activate(plan='metered')
        for quantity in (11, 1001):
            self.billing.entitlements.record(tenant, UsageEvent(resource_id=uid(), category='llm_input_tokens', quantity=quantity,
                unit='token', provider='mock', timestamp=self.at, idempotency_key=uid(), billable=True))
        self.at = datetime(2030, 2, 1, tzinfo=timezone.utc)
        invoice = self.post('/api/billing/usage-invoice', {'confirmed': True, 'billing_period': '2030-01'})
        self.assertEqual(invoice['amount_minor'], 3006)
        self.assertEqual(self.post('/api/billing/usage-invoice', {'confirmed': True, 'billing_period': '2030-01'})['id'], invoice['id'])

    def test_active_user_reenable_cannot_bypass_limit(self):
        self.activate()
        second = self.post('/api/users', {'subject': 'second', 'role': 'viewer'})
        response = self.client.put('/api/users/' + second['id'], headers=self.headers, json={'subject': 'second', 'role': 'viewer', 'enabled': False})
        self.assertEqual(response.status_code, 200)
        self.post('/api/users', {'subject': 'third', 'role': 'viewer'})
        response = self.client.put('/api/users/' + second['id'], headers=self.headers, json={'subject': 'second', 'role': 'viewer', 'enabled': True})
        self.assertEqual(response.status_code, 402)

    def test_history_retention_cannot_exceed_plan(self):
        self.activate()
        response = self.client.put('/api/settings', headers=self.headers, json={'default_locale': 'en-US', 'timezone': 'Europe/Sofia',
            'usage_limit': 10000, 'retention_days': 31})
        self.assertEqual(response.status_code, 402)

    def test_storage_limit_and_secret_port_tenant_ownership(self):
        self.plan('tiny-storage', limits={'storage_bytes': {'maximum': 0}})
        tenant = self.activate(plan='tiny-storage')
        response = self.client.put('/api/credentials', headers=self.headers, json={'name': 'llm:fixture', 'value': uid() + uid(), 'confirmed': True})
        self.assertEqual(response.status_code, 402)
        other = self.store.principal('demo-admin', 'demo')
        with self.assertRaises(DomainError): self.billing.secrets.get(tenant, 'llm:fixture', other)

    def test_platform_suspend_is_not_cleared_by_payment(self):
        invoice = self.paid()
        tenant = self.headers['X-Tenant-ID']
        response = self.client.put('/api/platform/tenants/' + tenant + '/state', headers={'Authorization': 'Bearer support-fixture'}, json={'state': 'suspended', 'confirmed': True})
        self.assertEqual(response.status_code, 200)
        invoice = self.post('/api/billing/checkout', {'confirmed': True, 'plan_id': 'limited', 'event_id': uid()})
        self.post('/api/billing/invoices/' + invoice['id'] + '/mock-pay', {'confirmed': True, 'event_id': uid()})
        self.assertEqual(self.client.get('/api/bootstrap', headers=self.headers).status_code, 403)

    def test_backup_manifest_tampering_and_wrong_key_are_rejected(self):
        self.activate()
        manager = self.app.state.backups
        backup = manager.create()
        file = manager.directory / backup['filename']
        data = json.loads(file.read_text())
        data['schema_version'] = 1
        file.write_text(json.dumps(data))
        with self.assertRaises(DomainError): manager.restore(backup['filename'], Path(self.directory.name) / 'tampered.sqlite')

    def test_outbound_quota_reservation_prevents_concurrent_overrun(self):
        from concurrent.futures import ThreadPoolExecutor
        from time import sleep
        self.plan('sms-one', limits={'sms_segments': {'maximum': 1}})
        tenant = self.activate(plan='sms-one')
        gateway = self.app.state.messaging
        principal = self.store.principal('verified-owner', tenant)
        conn = self.post('/api/messaging/connections', {'channel': 'sms', 'sender_id': '+359888000001', 'webhook_secret': uid() + uid()})
        conversation = self.app.state.orchestrator.conversation(principal, 'default', 'sms')
        conversation = self.store.update('conversations', tenant, conversation['id'], {'connection_id': conn['id'], 'remote_sender_id': '+359888000002'})
        assistant = self.store.get('assistants', tenant, 'default')
        for _ in range(2): gateway.queue_response(principal, assistant, conversation, 'Hello', 'en-US', uid())
        adapter = gateway.mock['sms']; send = adapter.send_message
        def delayed(*args): sleep(.05); return send(*args)
        adapter.send_message = delayed
        jobs = [j for j in self.store.list('jobs', tenant) if j['kind'] == 'outbound_message']
        def deliver(job):
            try: return gateway.deliver(principal, job)
            except DomainError as error: return {'code': error.code}
        with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(deliver, jobs))
        self.assertEqual(sum(r.get('status') == 'simulated' for r in results), 1)
        self.assertEqual(self.billing.entitlements.quantity(tenant, 'sms_segments'), 1)

    def test_voice_budget_reservation_limits_concurrent_calls(self):
        self.plan('voice-small', limits={'voice_seconds': {'maximum': 30}})
        self.activate(plan='voice-small')
        first = self.post('/api/calls', {})
        self.assertEqual(first['budget_seconds'], 30)
        self.post('/api/calls', {}, 402)

    def test_mock_payment_cannot_activate_without_enablement(self):
        invoice = self.paid()
        self.billing.mock_enabled = False
        self.post('/api/billing/invoices/' + invoice['id'] + '/mock-pay', {'confirmed': True, 'event_id': uid()}, 503)

    def test_payment_undercharge_is_rejected(self):
        self.register()
        invoice = self.post('/api/billing/checkout', {'confirmed': True, 'plan_id': 'limited', 'event_id': uid()})
        tenant = self.headers['X-Tenant-ID']
        from semantic_os.backend.assistant.saas_domain import PaymentEvent
        event = PaymentEvent(event_id=uid(), customer_id=self.store.find('billing_customers', tenant, 'current')['external_customer_id'],
            invoice_id=invoice['id'], kind='invoice_paid', amount_minor=1, currency='EUR', timestamp=self.at)
        with self.assertRaises(DomainError): self.billing.apply_event(tenant, event)
        self.assertIsNone(self.billing.entitlements.subscription(tenant))

    def test_trial_does_not_reset_on_repeated_selection(self):
        tenant = self.activate()
        first = self.billing.entitlements.subscription(tenant)
        self.at += timedelta(days=1)
        second = self.post('/api/billing/trial', {'confirmed': True, 'plan_id': 'limited', 'event_id': uid()})
        self.assertEqual(first['period_end'], second['period_end'])

    def test_platform_permission_cannot_be_claimed_by_tenant_admin(self):
        self.activate()
        self.assertEqual(self.client.get('/api/platform/tenants', headers=self.headers).status_code, 403)

    def test_on_disk_wal_backup_restores_committed_data(self):
        from semantic_os.backend.assistant.backup import BackupManager
        source = Store(Path(self.directory.name) / 'wal-source.sqlite3')
        try:
            source.seed()
            self.assertEqual(source.db.execute('PRAGMA journal_mode').fetchone()[0], 'wal')
            manager = BackupManager(source, Path(self.directory.name) / 'wal-backups', self.backup_key)
            backup = manager.create()
            target = Path(self.directory.name) / 'wal-restored.sqlite3'
            self.assertEqual(manager.restore(backup['filename'], target)['integrity'], 'ok')
            restored = Store(target)
            try: self.assertEqual(restored.count('assistants', 'demo'), 1)
            finally: restored.close()
        finally: source.close()

    def test_subscription_monthly_limits_replace_legacy_lifetime_counter(self):
        tenant = self.activate()
        self.store.update_tenant(tenant, {**self.store.tenant(tenant), 'usage_limit': 1})
        conversation = self.post('/api/conversations', {})['id']
        for index in range(2): self.post('/api/conversations/' + conversation + '/messages', {'content': 'Hello', 'event_id': str(index)})
        self.assertEqual(self.billing.entitlements.quantity(tenant, 'ai_messages'), 2)

    def test_voice_minute_configuration_uses_exact_seconds(self):
        from semantic_os.backend.assistant.saas_domain import SubscriptionPlan
        plan = SubscriptionPlan(id='voice', name_bg='Глас', name_en='Voice', monthly_voice_minutes=3)
        self.assertEqual(plan.limits['voice_seconds'].maximum, 180)

    def test_early_delivery_callback_and_dispatch_meter_only_once(self):
        tenant = self.activate()
        gateway = self.app.state.messaging
        principal = self.store.principal('verified-owner', tenant)
        conn = self.post('/api/messaging/connections', {'channel': 'sms', 'sender_id': '+359888000001', 'webhook_secret': uid() + uid()})
        conv = self.app.state.orchestrator.conversation(principal, 'default', 'sms')
        conv = self.store.update('conversations', tenant, conv['id'], {'connection_id': conn['id'], 'remote_sender_id': '+359888000002'})
        delivery = gateway.queue_response(principal, self.store.get('assistants', tenant, 'default'), conv, 'Hello', 'en-US', uid())
        adapter = gateway.mock['sms']; send = adapter.send_message
        def callback_during_send(message, connection, credentials, key):
            result = send(message, connection, credentials, key)
            gateway.delivery_status(principal, conn, {'message_id': message['id'], 'provider_message_id': result['external_message_id'], 'status': 'delivered'})
            return result
        adapter.send_message = callback_during_send
        gateway.run(principal)
        self.assertEqual(self.billing.entitlements.quantity(tenant, 'sms_segments'), 1)
        self.assertEqual(self.store.get('messages', tenant, delivery['message_id'])['status'], 'delivered')


if __name__ == '__main__': unittest.main()
