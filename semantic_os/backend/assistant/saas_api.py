"""SaaS control plane. Tenant membership and independent platform authority are separate."""
from datetime import datetime, timedelta
import json
from typing import Literal
from fastapi import Depends, Request
from pydantic import Field, SecretStr
from .domain import Contract, DomainError, Principal
from .saas_domain import RegisterOrganization, SubscriptionPlan, UsageEvent, UNITS
from .store import uid, now
from .jobs import UNRESOLVED_JOB_STATUSES


class Confirmation(Contract):
    confirmed: Literal[True]

class InvoiceAdjustment(Confirmation):
    amount_minor_text:str=Field(pattern=r'^[1-9]\d{0,17}$')
    kind:Literal['credit','refund']
    reason:Literal['service_issue','duplicate_charge','goodwill']
    event_id:str=Field(min_length=1,max_length=100)


class VerifyEmail(Contract):
    token: SecretStr | None = None


class PlanSelection(Confirmation):
    plan_id: str
    interval: Literal['monthly', 'annual'] = 'monthly'
    event_id: str = Field(min_length=1, max_length=100)


class PayInvoice(Confirmation):
    event_id: str = Field(min_length=1, max_length=100)
    success: bool = True


class CredentialUpdate(Confirmation):
    name: str = Field(min_length=1, max_length=200)
    value: SecretStr


class Reconciliation(Contract):
    billing_period: str = Field(pattern=r'^\d{4}-\d{2}$')
    observed: dict[str, int]
    event_id: str = Field(min_length=1, max_length=100)


class UsageInvoice(Confirmation):
    billing_period: str = Field(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')


class SupportGrant(Confirmation):
    support_subject: str = Field(min_length=1, max_length=200)
    expires_minutes: int = Field(default=15, ge=1, le=30)
    reason: str = Field(min_length=1, max_length=200)


class TenantState(Confirmation):
    state: Literal['active', 'suspended']


def register_saas(app, billing, identity, actor, platform_subjects, privacy, backups):
    store, secret_store = billing.store, billing.secrets

    def identity_actor(request: Request):
        return identity.verify_identity(request.headers.get('authorization'), request.client.host if request.client else '')

    def platform_actor(request: Request):
        subject = identity_actor(request)
        if subject.subject not in platform_subjects: raise DomainError('forbidden', 403)
        return subject

    def platform_audit(subject, action, resource=''):
        from .observability import correlation_id
        with store.transaction():
            store.db.execute('INSERT INTO platform_audit VALUES(?,?,?)', (uid(), json.dumps({'subject': subject.subject,
                'action': action, 'resource_id': resource, 'correlation_id': correlation_id.get()}), now()))

    @app.get('/api/saas/plans')
    def plans(): return billing.plans()

    @app.put('/api/platform/plans')
    def save_plan(config: SubscriptionPlan, subject=Depends(platform_actor)):
        result = billing.save_plan(config)
        platform_audit(subject, 'plan:configured', config.id)
        return result

    @app.post('/api/saas/register', status_code=201)
    def register(config: RegisterOrganization, subject=Depends(identity_actor)):
        return billing.register(subject, config)

    @app.get('/api/saas/onboarding')
    def onboarding(principal: Principal = Depends(actor)): return billing.onboarding(principal)

    @app.get('/api/saas/access')
    def access(principal: Principal = Depends(actor)):
        tenant = store.tenant(principal.tenant_id)
        return {'role': principal.role, 'tenant_id': principal.tenant_id, 'state': tenant.get('onboarding_state', 'active'),
            'timezone': tenant['timezone'], 'default_locale': tenant['default_locale']}

    @app.post('/api/saas/onboarding/verify')
    def verify(config: VerifyEmail, principal: Principal = Depends(actor), subject=Depends(identity_actor)):
        return billing.verify(principal, subject, config.token.get_secret_value() if config.token else None)

    @app.get('/api/saas/onboarding/mock-email')
    def mock_email(principal: Principal = Depends(actor)):
        principal.require('configure')
        if not billing.verification_mock: raise DomainError('forbidden', 403)
        return {'provider': 'MOCK', 'token': secret_store.get(principal.tenant_id, 'onboarding:mock-verification', principal)}

    @app.get('/api/billing')
    def overview(principal: Principal = Depends(actor)):
        principal.require('configure')
        return billing.overview(principal)

    @app.post('/api/billing/trial')
    def trial(config: PlanSelection, principal: Principal = Depends(actor)):
        return billing.select_trial(principal, config.plan_id, config.interval)

    @app.post('/api/billing/checkout')
    def checkout(config: PlanSelection, principal: Principal = Depends(actor)):
        return billing.checkout(principal, config.plan_id, config.interval, config.event_id)

    @app.post('/api/billing/change')
    def change(config: PlanSelection, principal: Principal = Depends(actor)):
        return billing.change(principal, config.plan_id, config.interval, config.event_id)

    @app.post('/api/billing/cancel')
    def cancel(config: Confirmation, principal: Principal = Depends(actor)): return billing.cancel(principal)

    @app.post('/api/billing/invoices/{id}/mock-pay')
    def pay(id: str, config: PayInvoice, principal: Principal = Depends(actor)):
        return billing.mock_pay(principal, id, config.event_id, success=config.success)

    @app.post('/api/billing/invoices/{id}/adjustments')
    def adjust(id:str,config:InvoiceAdjustment,principal:Principal=Depends(actor)):
        return billing.adjust_invoice(principal,id,config)

    @app.post('/webhooks/payments/{tenant_id}')
    async def payment_webhook(tenant_id: str, request: Request):
        if request.query_params: raise DomainError('invalid_input', 422)
        with store.operations.span('billing_webhook', tenant_id):
            return billing.webhook(tenant_id, await request.body(), request.headers.get('x-signature', ''))

    @app.get('/api/usage')
    def usage(principal: Principal = Depends(actor)): return billing.entitlements.summary(principal.tenant_id)

    @app.post('/api/billing/usage-report')
    def report(config: UsageEvent, principal: Principal = Depends(actor)):
        principal.require('configure')
        if config.billable or config.provider != 'mock' or not billing.mock_enabled: raise DomainError('forbidden', 403)
        return billing.entitlements.record(principal.tenant_id, config)

    @app.put('/api/billing/mock-provider')
    def mock_provider(config: CredentialUpdate, principal: Principal = Depends(actor)):
        principal.require('configure')
        if not billing.mock_enabled or config.name != 'payment:webhook_secret': raise DomainError('forbidden', 403)
        value = config.value.get_secret_value()
        if len(value) < 32: raise DomainError('invalid_input', 422)
        with billing.entitlements.provisioning(): secret_store.put(principal.tenant_id, config.name, value, principal)
        return {'provider': 'mock', 'state': 'MOCK', 'real_charges_enabled': False}

    @app.post('/api/billing/reconciliation')
    def reconciliation(config: Reconciliation, principal: Principal = Depends(actor)):
        principal.require('configure')
        if set(config.observed) - set(UNITS) or any(v < 0 for v in config.observed.values()): raise DomainError('invalid_input', 422)
        key = 'reconcile:' + config.event_id
        from hashlib import sha256
        fingerprint = sha256(config.model_dump_json().encode()).hexdigest()
        existing = store.find('reconciliation_reports', principal.tenant_id, key)
        if existing:
            if existing.get('fingerprint') != fingerprint: raise DomainError('conflict', 409)
            return existing
        differences = {k: {'internal': billing.entitlements.quantity(principal.tenant_id, k, config.billing_period),
            'provider': v, 'difference': v - billing.entitlements.quantity(principal.tenant_id, k, config.billing_period)} for k, v in config.observed.items()}
        result = store.add('reconciliation_reports', principal.tenant_id, {'billing_period': config.billing_period,
            'differences': differences, 'fingerprint': fingerprint, 'status': 'review_required', 'automatically_charged': False}, external_key=key)
        store.audit(principal, 'billing:reconciliation', resource_id=result['id'])
        return result

    @app.post('/api/billing/usage-invoice')
    def usage_invoice(config: UsageInvoice, principal: Principal = Depends(actor)):
        return billing.usage_invoice(principal, config.billing_period)

    @app.get('/api/credentials')
    def credentials(principal: Principal = Depends(actor)):
        principal.require('configure')
        return [{k: s.get(k) for k in ('id', 'name', 'version', 'state', 'rotated_at', 'revoked_at')} for s in store.list('secrets', principal.tenant_id)
            if not s['name'].startswith(('attachment:', 'recording:', 'transcript:', 'onboarding:'))]

    @app.put('/api/credentials')
    def credential(config: CredentialUpdate, principal: Principal = Depends(actor)):
        principal.require('configure')
        if not config.name.startswith(('voice:', 'telephony:', 'messaging:', 'payment:', 'llm:', 'stt:', 'tts:', 'email:', 'connection:')): raise DomainError('invalid_input', 422)
        value = config.value.get_secret_value()
        if not 16 <= len(value) <= 10000: raise DomainError('invalid_input', 422)
        secret_store.put(principal.tenant_id, config.name, value, principal)
        return {'status': 'stored', 'masked': True}

    @app.post('/api/credentials/{id}/revoke')
    def revoke(id: str, config: Confirmation, principal: Principal = Depends(actor)): return secret_store.revoke(principal, id)

    @app.post('/api/credentials/rotate-keyring')
    def rotate(config: Confirmation, principal: Principal = Depends(actor)): return secret_store.rotate_keyring(principal)

    @app.get('/api/operations')
    def operations(principal: Principal = Depends(actor)):
        principal.require('approve')
        return {**store.operations.snapshot(principal.tenant_id), 'failed_jobs': [{k: j.get(k) for k in ('id', 'kind', 'status', 'error_code', 'attempts', 'due_at')} for j in store.list('jobs', principal.tenant_id) if j['status'] in UNRESOLVED_JOB_STATUSES],
            'connections': [{k: c.get(k) for k in ('id', 'channel', 'provider', 'state', 'enabled', 'last_error')} for c in store.list('channel_connections', principal.tenant_id)],
            'schema_version': 5, 'topology': 'single_process_sqlite'}

    @app.get('/api/platform/tenants')
    def platform_tenants(subject=Depends(platform_actor)):
        with store.lock: tenants = [json.loads(r['data']) for r in store.db.execute('SELECT data FROM tenants')]
        platform_audit(subject, 'platform:tenant_overview')
        return [{'id': t['id'], 'name': t['name'], 'state': t.get('onboarding_state', 'legacy'),
            'subscription_status': (billing.entitlements.subscription(t['id']) or {}).get('status', 'unconfigured'),
            'counts': {table: store.count(table, t['id']) for table in ('users', 'assistants', 'channel_connections')}} for t in tenants]

    @app.get('/api/platform/operations')
    def platform_operations(subject=Depends(platform_actor)):
        platform_audit(subject, 'platform:operations_read')
        return store.operations.snapshot('')

    @app.post('/api/support/grants')
    def grant(config: SupportGrant, principal: Principal = Depends(actor)):
        principal.require('configure')
        if config.support_subject not in platform_subjects: raise DomainError('forbidden', 403)
        row = store.add('support_grants', principal.tenant_id, {'subject': config.support_subject, 'reason': config.reason,
            'scope': 'conversation_read', 'status': 'active', 'expires_at': (billing.clock() + timedelta(minutes=config.expires_minutes)).isoformat()})
        store.audit(principal, 'support:authorized', resource_id=row['id'])
        return row

    @app.put('/api/platform/tenants/{id}/state')
    def tenant_state(id: str, config: TenantState, subject=Depends(platform_actor)):
        tenant = store.tenant(id)
        if tenant.get('onboarding_state') == 'cancelled': raise DomainError('tenant_cancelled', 403)
        if config.state == 'active':
            subscription = billing.entitlements.subscription(id)
            if not tenant.get('email_verified') or not subscription or subscription['status'] not in ('trialing', 'active', 'past_due'):
                raise DomainError('subscription_required', 402)
        tenant.update(onboarding_state=config.state, platform_suspended=config.state == 'suspended')
        store.update_tenant(id, tenant)
        platform_audit(subject, 'tenant:' + config.state, id)
        return {'id': id, 'state': config.state}

    @app.get('/api/platform/support/{tenant_id}/conversations/{id}/messages')
    def support_messages(tenant_id: str, id: str, subject=Depends(platform_actor)):
        grant = next((g for g in store.list('support_grants', tenant_id) if g['subject'] == subject.subject and g['status'] == 'active' and datetime.fromisoformat(g['expires_at']) > billing.clock()), None)
        if not grant: raise DomainError('forbidden', 403)
        store.get('conversations', tenant_id, id)
        principal = Principal(tenant_id, 'support-service', 'viewer', subject.subject)
        store.audit(principal, 'support:conversation_read', resource_id=id)
        platform_audit(subject, 'support:conversation_read', id)
        return store.list('messages', tenant_id, id)[-100:]

    @app.get('/api/privacy/export')
    def export(principal: Principal = Depends(actor)): return privacy.export(principal)

    @app.get('/api/privacy/contacts/{id}/export')
    def contact_export(id: str, principal: Principal = Depends(actor)): return privacy.export(principal, id)

    @app.post('/api/support/grants/{id}/revoke')
    def revoke_grant(id: str, config: Confirmation, principal: Principal = Depends(actor)):
        principal.require('configure')
        row = store.update('support_grants', principal.tenant_id, id, {'status': 'revoked'})
        store.audit(principal, 'support:revoked', resource_id=id)
        return row

    @app.post('/api/privacy/requests')
    def privacy_request(config: privacy.RequestModel, principal: Principal = Depends(actor)): return privacy.request(principal, config)

    @app.post('/api/privacy/requests/{id}/execute')
    def privacy_execute(id: str, config: Confirmation, principal: Principal = Depends(actor)): return privacy.execute(principal, id)

    @app.post('/api/backups')
    def backup(config: Confirmation, principal: Principal = Depends(actor)):
        principal.require('configure')
        # Backups contain every tenant: creation is additionally platform-restricted.
        if principal.subject not in platform_subjects: raise DomainError('forbidden', 403)
        result = backups.create()
        store.audit(principal, 'backup:created', resource_id=result['id'])
        return result
