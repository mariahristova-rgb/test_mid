"""Tenant lifecycle and conventional subscription state machine with mock payments."""
import calendar
from datetime import datetime, timedelta
from hashlib import sha256
import hmac
import json
import os
import secrets as random_secrets
from .domain import DomainError, Principal
from .saas_domain import SubscriptionPlan, PaymentEvent
from .store import uid, now, event_key
from .payments import MockPaymentProvider
from .entitlements import PlanEntitlementService
from .messaging_adapters import mailbox
from .language import tr


def advance(at, interval):
    month = at.month + (12 if interval == 'annual' else 1)
    year, month = at.year + (month - 1) // 12, (month - 1) % 12 + 1
    return at.replace(year=year, month=month, day=min(at.day, calendar.monthrange(year, month)[1]))


class BillingService:
    def __init__(self, store, secret_store, clock, *, demo=False):
        self.store, self.secrets, self.clock = store, secret_store, clock
        self.provider = MockPaymentProvider()
        self.mock_enabled = demo or os.getenv('ASSISTANT_ALLOW_MOCK_BILLING') == 'true'
        self.verification_mock = demo and os.getenv('ASSISTANT_ENV', 'development') not in ('production', 'staging')
        self.entitlements = PlanEntitlementService(store, self, clock)
        store.entitlements = self.entitlements
        if demo and not self.plans():
            self.save_plan(SubscriptionPlan(id='sandbox', name_bg='Тестов план', name_en='Sandbox plan', trial_days=14,
                limits={key: {'maximum': maximum} for key, maximum in {'assistants': 10, 'agents': 2, 'users': 20,
                    'connections': 20, 'ai_messages': 10000, 'voice_seconds': 36000, 'sms_segments': 10000,
                    'whatsapp_messages': 10000, 'email_messages': 10000, 'tool_executions': 10000,
                    'storage_bytes': 100000000}.items()}))

    def plans(self):
        with self.store.lock: return [json.loads(r['data']) for r in self.store.db.execute('SELECT data FROM saas_plans ORDER BY id')]

    def save_plan(self, config):
        data = config.model_dump(mode='json')
        with self.store.transaction():
            previous = self.store.db.execute('SELECT data FROM saas_plans WHERE id=?', (config.id,)).fetchone()
            data['version'] = json.loads(previous['data']).get('version', 0) + 1 if previous else 1
            data['monthly_minor_text'], data['annual_minor_text'] = str(config.monthly_minor), str(config.annual_minor)
            self.store.db.execute('INSERT INTO saas_plans VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data', (config.id, json.dumps(data), now()))
        return data

    def plan(self, id):
        result = next((p for p in self.plans() if p['id'] == id), None)
        if not result or not result['enabled']: raise DomainError('not_found', 404)
        return result

    def register(self, subject, config):
        email = mailbox(config.email)
        plan = self.plan(config.plan_id)
        if any(plan['limits'].get(key, {}).get('maximum', minimum) < minimum for key, minimum in [('users', 1), ('assistants', 1), ('agents', 2)]):
            raise DomainError('upgrade_required', 402)
        fingerprint = sha256(config.model_dump_json().encode()).hexdigest()
        key = event_key('registration:' + subject.subject, config.event_id)
        with self.store.transaction(), self.entitlements.provisioning():
            for row in self.store.db.execute('SELECT tenant_id,data FROM onboarding_events WHERE external_key=?', (key,)).fetchall():
                data = json.loads(row['data'])
                if data['fingerprint'] != fingerprint: raise DomainError('conflict', 409)
                return self.onboarding(self.store.principal(subject.subject, row['tenant_id']))
            verified_email = getattr(subject, 'email', '')
            verified = getattr(subject, 'email_verified', False) is True and verified_email and mailbox(verified_email) == email
            tenant_id = uid()
            self.store.seed(tenant_id, subject.subject)
            self.store.add('onboarding_events', tenant_id, {'state': 'created', 'timestamp': self.clock().isoformat()})
            tenant = self.store.tenant(tenant_id)
            tenant.update(name=config.name, default_locale=config.default_locale, timezone=config.timezone,
                onboarding_state='configuring' if verified else 'pending_verification', email_verified=bool(verified),
                administrator_email=email, owner_subject=subject.subject, chosen_plan_id=plan['id'], chosen_interval=config.interval,
                retention_days=plan['retention_days'], created_at=self.clock().isoformat())
            self.store.update_tenant(tenant_id, tenant)
            self.store.update('assistants', tenant_id, 'default', {'default_locale': config.default_locale})
            principal = self.store.principal(subject.subject, tenant_id)
            self.store.update('users', tenant_id, principal.user_id, {'preferred_locale': config.default_locale})
            self.store.add('billing_customers', tenant_id, self.provider.create_customer(tenant_id), external_key='current')
            self.store.add('onboarding_events', tenant_id, {'fingerprint': fingerprint, 'state': tenant['onboarding_state'], 'timestamp': self.clock().isoformat()}, external_key=key)
            if not verified and self.verification_mock:
                token = random_secrets.token_urlsafe(32)
                self.store.add('verification_tokens', tenant_id, {'token_hash': sha256(token.encode()).hexdigest(),
                    'subject': subject.subject, 'status': 'pending', 'expires_at': (self.clock() + timedelta(minutes=30)).isoformat()})
                self.secrets.put(tenant_id, 'onboarding:mock-verification', token)
            self.store.audit(principal, 'tenant:registered')
            return self.onboarding(principal)

    def onboarding(self, principal):
        tenant = self.store.tenant(principal.tenant_id)
        if tenant.get('owner_subject') != principal.subject and principal.role != 'admin': raise DomainError('forbidden', 403)
        return {'tenant_id': principal.tenant_id, 'state': tenant.get('onboarding_state', 'active'),
            'email_verified': tenant.get('email_verified', True), 'default_locale': tenant['default_locale'], 'timezone': tenant['timezone'],
            'plan_id': tenant.get('chosen_plan_id'), 'interval': tenant.get('chosen_interval', 'monthly'),
            'verification_provider': 'MOCK' if self.verification_mock else 'VERIFIED_IDENTITY',
            'verification_message': tr(tenant['default_locale'], 'verification_sent'), 'subscription': self.entitlements.subscription(principal.tenant_id)}

    def verify(self, principal, subject, token=None):
        principal.require('configure')
        tenant = self.store.tenant(principal.tenant_id)
        if tenant.get('owner_subject') != subject.subject: raise DomainError('forbidden', 403)
        verified = getattr(subject, 'email_verified', False) is True and mailbox(getattr(subject, 'email', '')) == tenant['administrator_email']
        if verified and tenant.get('email_verified'): return self.onboarding(principal)
        with self.store.transaction():
            if token:
                if not self.verification_mock: raise DomainError('forbidden', 403)
                candidate = next((v for v in self.store.list('verification_tokens', principal.tenant_id) if v['subject'] == subject.subject and
                    hmac.compare_digest(v['token_hash'], sha256(token.encode()).hexdigest())), None)
                if not candidate or candidate['status'] != 'pending' or datetime.fromisoformat(candidate['expires_at']) < self.clock(): raise DomainError('expired', 409)
                self.store.update('verification_tokens', principal.tenant_id, candidate['id'], {'status': 'used'})
                verified = True
            if not verified: raise DomainError('verification_required', 403)
            tenant.update(email_verified=True, onboarding_state='configuring')
            self.store.update_tenant(principal.tenant_id, tenant)
            self.store.audit(principal, 'tenant:verified')
            return self.onboarding(principal)

    def select_trial(self, principal, plan_id, interval):
        principal.require('configure')
        tenant = self.store.tenant(principal.tenant_id)
        if not tenant.get('email_verified'): raise DomainError('verification_required', 403)
        plan = self.plan(plan_id)
        if not plan['trial_days']: raise DomainError('subscription_required', 402)
        with self.store.transaction():
            previous = self.entitlements.subscription(principal.tenant_id)
            if previous: return previous  # A trial is never reset by repeated requests or plan changes.
            start = self.clock()
            end = start + timedelta(days=plan['trial_days'])
            return self.new_subscription(principal, plan, interval, 'trialing', start, end)

    def new_subscription(self, principal, plan, interval, status, start, end):
        customer = self.store.find('billing_customers', principal.tenant_id, 'current')
        if customer.get('currency') and customer['currency'] != plan['currency']: raise DomainError('invalid_input', 422)
        self.store.update('billing_customers', principal.tenant_id, customer['id'], {'currency': plan['currency']})
        row = {**self.provider.create_subscription(customer, plan, interval), 'plan_id': plan['id'], 'plan_snapshot': plan,
            'interval': interval, 'status': status, 'period_start': start.isoformat(), 'period_end': end.isoformat(),
            'activated_at': start.isoformat(),
            'cancel_at_period_end': False, 'pending_change': None, 'grace_until': (end + timedelta(days=plan['grace_days'])).isoformat()}
        existing = self.entitlements.subscription(principal.tenant_id)
        row['revision'] = (existing or {}).get('revision', 0) + 1
        result = self.store.update('subscriptions', principal.tenant_id, existing['id'], row) if existing else self.store.add('subscriptions', principal.tenant_id, row, external_key='current')
        self.store.add('subscription_items', principal.tenant_id, {'subscription_id': result['id'], 'plan_id': plan['id'], 'plan_version': plan['version'],
            'interval': interval, 'timestamp': self.clock().isoformat()})
        tenant = self.store.tenant(principal.tenant_id)
        tenant.update(onboarding_state='suspended' if tenant.get('platform_suspended') else 'active', retention_days=min(tenant['retention_days'], plan['retention_days']))
        self.store.update_tenant(principal.tenant_id, tenant)
        self.store.audit(principal, 'subscription:' + status, resource_id=result['id'])
        self.notify(principal, 'subscription_active')
        return result

    def notify(self, principal, key):
        tenant = self.store.tenant(principal.tenant_id)
        self.store.add('onboarding_events', principal.tenant_id, {'kind': 'billing_notification', 'locale': tenant['default_locale'],
            'subject': tr(tenant['default_locale'], 'billing_subject'), 'body': tr(tenant['default_locale'], key),
            'delivery_status': 'mock_prepared', 'timestamp': self.clock().isoformat()})

    def checkout(self, principal, plan_id, interval, request_id):
        principal.require('configure')
        tenant = self.store.tenant(principal.tenant_id)
        if not tenant.get('email_verified'): raise DomainError('verification_required', 403)
        if not self.mock_enabled: raise DomainError('unconfigured', 503)
        plan = self.plan(plan_id)
        customer = self.store.find('billing_customers', principal.tenant_id, 'current')
        if customer.get('currency') and customer['currency'] != plan['currency']: raise DomainError('invalid_input', 422)
        with self.store.transaction():
            key = event_key('checkout', request_id)
            previous = self.store.find('billing_invoices', principal.tenant_id, key)
            if previous:
                if previous['plan_id'] != plan_id or previous['interval'] != interval: raise DomainError('conflict', 409)
                return previous
            amount = plan['monthly_minor' if interval == 'monthly' else 'annual_minor']
            invoice = self.store.add('billing_invoices', principal.tenant_id, {'plan_id': plan_id, 'plan_snapshot': plan,
                'interval': interval, 'amount_minor': amount, 'amount_minor_text': str(amount), 'currency': plan['currency'], 'status': 'open', 'provider': 'mock',
                'created_at': self.clock().isoformat(), 'billing_period': self.entitlements.period(), 'purpose': 'subscription'}, external_key=key)
            invoice = self.store.update('billing_invoices', principal.tenant_id, invoice['id'], {'subscription_revision': (self.entitlements.subscription(principal.tenant_id) or {}).get('revision', 0)})
            checkout = self.provider.create_checkout(invoice, request_id)
            return self.store.update('billing_invoices', principal.tenant_id, invoice['id'], checkout)

    def webhook(self, tenant, raw, signature):
        if not self.mock_enabled: raise DomainError('unconfigured', 503)
        credential = self.secrets.get(tenant, 'payment:webhook_secret')
        event = self.provider.verify_webhook(raw, signature, credential)
        return self.apply_event(tenant, event)

    def apply_event(self, tenant, event: PaymentEvent):
        fingerprint = sha256(event.model_dump_json().encode()).hexdigest()
        with self.store.transaction():
            existing = self.store.find('payment_events', tenant, event.event_id)
            if existing:
                if existing['fingerprint'] != fingerprint: raise DomainError('conflict', 409)
                return {'duplicate': True, 'status': existing['status']}
            if abs((self.clock() - event.timestamp).total_seconds()) > 300: raise DomainError('expired', 409)
            customer = self.store.find('billing_customers', tenant, 'current')
            if not customer or customer['external_customer_id'] != event.customer_id: raise DomainError('forbidden', 403)
            invoice = self.store.get('billing_invoices', tenant, event.invoice_id)
            if invoice['amount_minor'] != event.amount_minor or invoice['currency'] != event.currency: raise DomainError('conflict', 409)
            owner = self.store.tenant(tenant)['owner_subject']
            principal = Principal(tenant, 'billing-service', 'admin', 'billing-service')
            if event.kind == 'invoice_paid':
                if invoice['status'] != 'paid':
                    subscription = self.entitlements.subscription(tenant)
                    if invoice.get('purpose') != 'usage' and invoice.get('subscription_revision', 0) != (subscription or {}).get('revision', 0):
                        raise DomainError('invalid_transition', 409)
                    self.store.update('billing_invoices', tenant, invoice['id'], {'status': 'paid', 'paid_at': event.timestamp.isoformat()})
                    start = self.clock()
                    if invoice.get('purpose') != 'usage': self.new_subscription(principal, invoice['plan_snapshot'], invoice['interval'], 'active', start, advance(start, invoice['interval']))
            elif invoice['status'] not in ('paid', 'failed'):
                self.store.update('billing_invoices', tenant, invoice['id'], {'status': 'failed'})
                subscription = self.entitlements.subscription(tenant)
                if subscription and subscription['status'] != 'past_due':
                    end = datetime.fromisoformat(subscription['period_end'])
                    self.store.update('subscriptions', tenant, subscription['id'], {'status': 'past_due',
                        'grace_until': (max(end, self.clock()) + timedelta(days=subscription['plan_snapshot']['grace_days'])).isoformat()})
                self.notify(principal, 'payment_failed')
            self.store.add('payment_events', tenant, {'fingerprint': fingerprint, 'status': 'processed',
                'invoice_id': invoice['id'], 'kind': event.kind, 'timestamp': event.timestamp.isoformat()}, external_key=event.event_id)
            self.store.audit(principal, 'payment:' + event.kind, resource_id=invoice['id'])
            return {'duplicate': False, 'status': 'processed'}

    def mock_pay(self, principal, invoice_id, request_id, *, success=True):
        principal.require('configure')
        if not self.mock_enabled: raise DomainError('unconfigured', 503)
        invoice = self.store.get('billing_invoices', principal.tenant_id, invoice_id)
        previous = self.store.find('payment_events', principal.tenant_id, request_id)
        if previous:
            if previous['invoice_id'] != invoice_id or previous['kind'] != ('invoice_paid' if success else 'payment_failed'): raise DomainError('conflict', 409)
            return {'duplicate': True, 'status': previous['status']}
        customer = self.store.find('billing_customers', principal.tenant_id, 'current')
        event = PaymentEvent(event_id=request_id, customer_id=customer['external_customer_id'], invoice_id=invoice_id,
            kind='invoice_paid' if success else 'payment_failed', amount_minor=invoice['amount_minor'], currency=invoice['currency'], timestamp=self.clock())
        # The local hosted-checkout fixture uses the same verified-webhook contract.
        if not self.store.find('secrets', principal.tenant_id, 'payment:webhook_secret'):
            with self.entitlements.provisioning():
                self.secrets.put(principal.tenant_id, 'payment:webhook_secret', random_secrets.token_urlsafe(48))
        raw = event.model_dump_json().encode()
        credential = self.secrets.get(principal.tenant_id, 'payment:webhook_secret')
        signature = hmac.new(credential.encode(), raw, sha256).hexdigest()
        return self.webhook(principal.tenant_id, raw, signature)

    def change(self, principal, plan_id, interval, request_id):
        principal.require('configure')
        subscription = self.entitlements.subscription(principal.tenant_id)
        plan = self.plan(plan_id)
        for category in ('assistants', 'agents', 'users', 'connections'):
            limit = plan['limits'].get(category)
            if limit and limit['mode'] == 'hard' and self.entitlements.quantity(principal.tenant_id, category) > limit['maximum']:
                raise DomainError('upgrade_required', 402)
        if not subscription: return self.checkout(principal, plan_id, interval, request_id)
        if plan['rank'] > subscription['plan_snapshot']['rank']:
            return self.checkout(principal, plan_id, interval, request_id)  # Full-period upgrade; no unverified proration.
        self.store.audit(principal, 'subscription:change_scheduled', resource_id=subscription['id'])
        change = self.provider.update_subscription(subscription, {'pending_change': {'plan_id': plan_id, 'interval': interval}})
        return self.store.update('subscriptions', principal.tenant_id, subscription['id'], {'pending_change': change['pending_change']})

    def cancel(self, principal):
        principal.require('configure')
        subscription = self.entitlements.subscription(principal.tenant_id)
        if not subscription: raise DomainError('not_found', 404)
        self.store.audit(principal, 'subscription:cancellation_scheduled', resource_id=subscription['id'])
        return self.store.update('subscriptions', principal.tenant_id, subscription['id'], self.provider.cancel_subscription(subscription))

    def refresh(self, tenant):
        subscription = self.entitlements.subscription(tenant)
        if not subscription: return
        at = self.clock()
        end = datetime.fromisoformat(subscription['period_end'])
        state = subscription['status']
        if state in ('cancelled', 'expired', 'suspended'): return
        with self.store.transaction():
            if at >= end and subscription['cancel_at_period_end']:
                self.store.update('subscriptions', tenant, subscription['id'], {'status': 'cancelled'})
                row = self.store.tenant(tenant); row['onboarding_state'] = 'suspended'; self.store.update_tenant(tenant, row)
            elif state == 'trialing' and at >= end:
                self.store.update('subscriptions', tenant, subscription['id'], {'status': 'expired'})
                row = self.store.tenant(tenant); row['onboarding_state'] = 'suspended'; self.store.update_tenant(tenant, row)
            elif state == 'active' and at >= end:
                pending = subscription.get('pending_change')
                plan = self.plan(pending['plan_id']) if pending else subscription['plan_snapshot']
                interval = pending['interval'] if pending else subscription['interval']
                principal = Principal(tenant, 'billing-service', 'admin', 'billing-service')
                self.checkout(principal, plan['id'], interval, 'renewal:' + subscription['id'] + ':' + subscription['period_end'])
                self.store.update('subscriptions', tenant, subscription['id'], {'status': 'past_due', 'pending_change': None})
            elif state == 'past_due' and at >= datetime.fromisoformat(subscription['grace_until']):
                self.store.update('subscriptions', tenant, subscription['id'], {'status': 'suspended'})
                row = self.store.tenant(tenant); row['onboarding_state'] = 'suspended'; self.store.update_tenant(tenant, row)

    def overview(self, principal):
        self.refresh(principal.tenant_id)
        return {'state': 'MOCK', 'subscription': self.entitlements.subscription(principal.tenant_id),
            'customer': self.store.find('billing_customers', principal.tenant_id, 'current'),
            'invoices': self.store.list('billing_invoices', principal.tenant_id), 'usage': self.entitlements.summary(principal.tenant_id),
            'notifications': self.store.list('onboarding_events', principal.tenant_id), 'real_charges_enabled': False}

    def usage_invoice(self, principal, period):
        principal.require('configure')
        if period >= self.entitlements.period(): raise DomainError('invalid_input', 422)
        key = 'usage-invoice:' + period
        with self.store.transaction():
            previous = self.store.find('billing_invoices', principal.tenant_id, key)
            if previous: return previous
            subscription = self.entitlements.subscription(principal.tenant_id)
            if not subscription: raise DomainError('subscription_required', 402)
            records = [r for r in self.store.list('billing_usage', principal.tenant_id) if r['billing_period'] == period and r.get('charge_minor', 0) > 0]
            currency = subscription['plan_snapshot']['currency']
            if any(r['currency'] != currency for r in records): raise DomainError('invalid_input', 422)
            total = sum(r['charge_minor'] for r in records)
            return self.store.add('billing_invoices', principal.tenant_id, {'amount_minor': total, 'amount_minor_text': str(total), 'currency': currency,
                'status': 'open', 'provider': 'mock', 'purpose': 'usage', 'billing_period': period,
                'usage_record_ids': [r['id'] for r in records], 'created_at': self.clock().isoformat(), 'state': 'MOCK'}, external_key=key)
