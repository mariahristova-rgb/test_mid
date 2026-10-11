"""Central backend entitlements and append-only, idempotent conventional usage ledger."""
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from threading import local
from .domain import DomainError
from .saas_domain import UsageEvent, UNITS, RESOURCES
from .store import event_key


class PlanEntitlementService:
    def __init__(self, store, billing, clock):
        self.store, self.billing, self.clock = store, billing, clock
        self.context = local()

    @contextmanager
    def provisioning(self):
        old = getattr(self.context, 'provisioning', False)
        self.context.provisioning = True
        try: yield
        finally: self.context.provisioning = old

    def subscription(self, tenant):
        return self.store.find('subscriptions', tenant, 'current')

    def access(self, tenant, *, recovery=False):
        row = self.store.tenant(tenant)
        state = row.get('onboarding_state')
        if state == 'cancelled': raise DomainError('tenant_cancelled', 403)
        if recovery: return
        if state and (not row.get('email_verified') or state not in ('active',)):
            raise DomainError('verification_required' if not row.get('email_verified') else 'subscription_required', 403)
        subscription = self.subscription(tenant)
        if subscription:
            self.billing.refresh(tenant)
            subscription = self.subscription(tenant)
            if subscription['status'] not in ('active', 'trialing', 'past_due') or subscription['status'] == 'past_due' and datetime.fromisoformat(subscription['grace_until']) <= self.clock():
                raise DomainError('subscription_required', 402)
        elif os.getenv('ASSISTANT_ENV', '').lower() in ('production', 'staging'):
            raise DomainError('subscription_required', 402)

    def period(self, at=None): return (at or self.clock()).astimezone(timezone.utc).strftime('%Y-%m')

    def plan(self, tenant):
        subscription = self.subscription(tenant)
        return subscription['plan_snapshot'] if subscription else None

    def quantity(self, tenant, category, period=None):
        if category in RESOURCES.values():
            table = next(t for t, c in RESOURCES.items() if c == category)
            return sum(self.active(table, r) for r in self.store.list(table, tenant))
        if category == 'storage_bytes':
            return sum(len(s.get('encrypted', '').encode()) for s in self.store.list('secrets', tenant))
        with self.store.lock:
            return self.store.db.execute("SELECT coalesce(sum(json_extract(data,'$.quantity')),0) FROM billing_usage WHERE tenant_id=? AND json_extract(data,'$.category')=? AND json_extract(data,'$.billing_period')=?", (tenant, category, period or self.period())).fetchone()[0]

    def check(self, tenant, category, quantity=1):
        self.access(tenant)
        plan = self.plan(tenant)
        if not plan: return
        limit = plan['limits'].get(category)
        reserved = self.reserved(tenant, category)
        if limit and limit['mode'] == 'hard' and limit['overage_policy'] == 'block' and self.quantity(tenant, category) + reserved + quantity > limit['maximum']:
            raise DomainError('upgrade_required', 402)

    def remaining(self, tenant, category):
        plan = self.plan(tenant)
        limit = plan['limits'].get(category) if plan else None
        if not limit or limit['mode'] != 'hard' or limit['overage_policy'] != 'block': return None
        return max(0, limit['maximum'] - self.quantity(tenant, category))

    def reserved(self, tenant, category):
        return sum(r['quantity'] for r in self.store.list('usage_reservations', tenant) if r['category'] == category and r['status'] in ('reserved', 'uncertain') and r['billing_period'] == self.period())

    def reserve(self, tenant, category, quantity, operation_id):
        key = 'outbound:' + operation_id
        with self.store.transaction():
            previous = self.store.find('usage_reservations', tenant, key)
            if previous and previous['status'] in ('reserved', 'uncertain', 'settled'): return previous
            self.check(tenant, category, quantity)
            data = {'category': category, 'quantity': quantity, 'status': 'reserved', 'billing_period': self.period(),
                'timestamp': self.clock().isoformat(), 'plan_snapshot': self.plan(tenant), 'resource_id': operation_id}
            return self.store.update('usage_reservations', tenant, previous['id'], data) if previous else self.store.add('usage_reservations', tenant, data, external_key=key)

    def release(self, tenant, operation_id, state='released'):
        previous = self.store.find('usage_reservations', tenant, 'outbound:' + operation_id)
        if previous: self.store.update('usage_reservations', tenant, previous['id'], {'status': state})

    def record(self, tenant, event: UsageEvent, *, enforce=True, plan_snapshot=None):
        if event.category not in UNITS or UNITS[event.category] != event.unit: raise DomainError('invalid_input', 422)
        if event.timestamp > self.clock(): raise DomainError('invalid_input', 422)
        key = event_key('billing_usage', event.idempotency_key)
        payload = event.model_dump(mode='json',exclude_none=True)
        fingerprint = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        with self.store.transaction():
            existing = self.store.find('billing_usage', tenant, key)
            if existing:
                if existing['fingerprint'] != fingerprint: raise DomainError('conflict', 409)
                return existing
            if enforce: self.check(tenant, event.category, event.quantity)
            plan = plan_snapshot or self.plan(tenant)
            limit = (plan or {}).get('limits', {}).get(event.category)
            before = self.quantity(tenant, event.category, self.period(event.timestamp))
            overage = max(0, before + event.quantity - limit['maximum']) - max(0, before - limit['maximum']) if limit else 0
            charge = overage * limit['overage_minor_per_unit'] if limit and limit['overage_policy'] == 'meter' and event.billable else 0
            result = self.store.add('billing_usage', tenant, {**payload, 'fingerprint': fingerprint,
                'billing_period': self.period(event.timestamp), 'plan_id': (plan or {}).get('id'), 'plan_version': (plan or {}).get('version'),
                'charge_minor': charge, 'currency': (plan or {}).get('currency'), 'rate_snapshot': limit}, external_key=key)
            period=self.period(event.timestamp)
            total = self.quantity(tenant, event.category,period)
            thresholds=sorted(set([limit['warning_percent'],*limit.get('warning_thresholds',[])])) if limit else []
            for threshold in thresholds:
                if total*100 < limit['maximum']*threshold:continue
                warning_key = event_key('usage_warning', period + ':' + event.category + ':' + str(threshold))
                if not self.store.find('usage_warnings', tenant, warning_key):
                    self.store.add('usage_warnings', tenant, {'category': event.category, 'code': 'usage_warning','threshold_percent':threshold,
                        'maximum': limit['maximum'], 'billing_period': period, 'timestamp': self.clock().isoformat()}, external_key=warning_key)
            return result

    def before_add(self, table, tenant, record):
        if getattr(self.context, 'provisioning', False): return
        if table in RESOURCES and self.active(table, record): self.check(tenant, RESOURCES[table])
        if table == 'secrets' and record.get('encrypted'):
            self.check(tenant, 'storage_bytes', len(record['encrypted'].encode()))

    @staticmethod
    def active(table, record):
        return record.get('status', 'active') == 'active' if table == 'assistants' else record.get('enabled', True)

    def before_update(self, table, tenant, previous, record):
        if getattr(self.context, 'provisioning', False): return
        if table in RESOURCES and not self.active(table, previous) and self.active(table, record): self.check(tenant, RESOURCES[table])
        if table == 'secrets' and len(record.get('encrypted', '')) > len(previous.get('encrypted', '')):
            self.check(tenant, 'storage_bytes', len(record['encrypted']) - len(previous.get('encrypted', '')))

    def after_add(self, table, tenant, record):
        if table != 'usage_records': return
        kind, channel = record.get('kind'), record.get('channel')
        categories = {}
        if kind == 'agent_execution' and not record.get('billing_precharged'): categories = {'ai_messages': 1, 'agent_executions': 1}
        if kind == 'tool_execution' and not record.get('billing_precharged'): categories = {'tool_executions': 1, 'agent_executions': 1}
        if kind == 'outbound_message':
            if channel == 'sms': categories['sms_segments'] = record.get('segments', 0)
            if channel == 'email': categories['email_messages'] = 1
            if channel == 'whatsapp': categories['whatsapp_messages'] = 1
        if channel == 'voice' and 'duration_seconds' in record:
            from decimal import Decimal, ROUND_CEILING
            categories['voice_seconds'] = int(Decimal(str(record['duration_seconds'])).to_integral_value(rounding=ROUND_CEILING))
        for category in ('llm_input_tokens', 'llm_output_tokens', 'stt_seconds', 'tts_characters','llm_milliseconds','tts_audio_milliseconds'):
            if isinstance(record.get(category), int): categories[category] = record[category]
        for category, quantity in categories.items():
            self.record(tenant, UsageEvent(resource_id=record.get('message_id') or record.get('call_id') or record['id'], category=category,
                quantity=quantity, unit=UNITS[category], provider=record.get('provider', 'mock'), timestamp=datetime.fromisoformat(record['occurred_at']) if record.get('occurred_at') else self.clock(),
                correlation_id=record.get('correlation_id', ''), idempotency_key=record['id'] + ':' + category,
                assistant_id=record.get('assistant_id'),channel=record.get('channel'),
                billable=False), enforce=False, plan_snapshot=record.get('plan_snapshot'))  # Observed usage is retained if an operation overran its quota.

    def summary(self, tenant):
        plan = self.plan(tenant)
        return {'billing_period': self.period(), 'period_timezone': 'UTC', 'plan': plan,
            'usage': {category: {'quantity': self.quantity(tenant, category), 'unit': UNITS.get(category, 'resource'),
                'reserved_quantity': self.reserved(tenant, category),
                'limit': (plan or {}).get('limits', {}).get(category)} for category in (*RESOURCES.values(), *UNITS)},
            'warnings': [w for w in self.store.list('usage_warnings', tenant) if w['billing_period'] == self.period()],
            'llm_tokens_status': 'reported_events_only_missing_providers_not_zero', 'monetary_estimate_status': 'UNAVAILABLE_NOT_INFERRED_FROM_TOKENS'}
