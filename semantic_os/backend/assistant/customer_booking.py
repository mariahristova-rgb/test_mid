"""Google customer booking bridge on existing approval, jobs and appointment records.

Confirmation queues a durable job. External writes never run in the approval
transaction. Running/uncertain jobs reconcile by deterministic event ID only.
"""
from datetime import datetime, timedelta
from hashlib import sha256
from urllib.parse import quote
from .calendar import MockCalendarProvider
from .connector_adapters import OfflineProviderHTTP, ProviderAdapter
from .domain import DomainError
from .language import format_date, tr
from .store import now, uid


class CustomerBookingBridge:
    def __init__(self, service, engine, bindings, *, live_writes_approved=False):
        self.service, self.engine, self.store = service, engine, service.store
        self.bindings = dict(bindings)
        self.clock = engine.clock
        self.live_writes_approved = live_writes_approved
        self.state = 'MOCK' if isinstance(service.http, OfflineProviderHTTP) and service.http.__class__ is OfflineProviderHTTP else 'LIVE_UNVERIFIED'

    def supports(self, tenant):
        configured = self.store.find('operations_events', tenant, 'customer-booking-binding')
        return bool(configured.get('active')) if configured else tenant in self.bindings

    def policy(self, tenant):
        configured = self.store.find('operations_events', tenant, 'customer-booking-binding')
        current = self.store.tenant(tenant)
        return {**current, 'calendar_policy': configured['calendar_policy'], 'timezone': configured['timezone']} if configured and configured.get('calendar_policy') else current

    def context(self, tenant, *, write=False):
        configured = self.store.find('operations_events', tenant, 'customer-booking-binding')
        binding = configured if configured and configured.get('active') else self.bindings.get(tenant) if not configured else None
        if not binding:
            raise DomainError('unconfigured', 503)
        actor = self.store.principal(binding['subject'], tenant)
        self.service.guard(actor, 'google')
        row = self.service.row(actor, binding['connection_id'])
        if row['provider'] != 'google' or row['state'] not in ('connected_unverified', 'verified'):
            raise DomainError('unconfigured', 503)
        if 'availability' not in row['actions'] or write and 'create' not in row['actions']:
            raise DomainError('tool_denied', 403)
        if write and self.state != 'MOCK' and not self.live_writes_approved:
            raise DomainError('forbidden', 403)
        if len(row['resource_ids']) != 1 or not self.policy(tenant).get('calendar_policy'):
            raise DomainError('unconfigured', 503)
        resource = row['resource_ids'][0]
        discovered = {r['id']: r for r in self.service.resources(actor, row['id'])}
        if resource not in discovered or write and not discovered[resource]['writable']:
            raise DomainError('forbidden', 403)
        return actor, row, self.service.resolve_resource(actor,row,resource)

    def configure(self, actor, identity, revision, confirmed):
        actor.require('configure')
        if confirmed is not True:
            raise DomainError('forbidden', 403)
        self.service.guard(actor, 'google')
        row = self.service.row(actor, identity)
        if row['revision'] != revision or row['provider'] != 'google' or len(row['resource_ids']) != 1:
            raise DomainError('conflict', 409)
        if not {'availability', 'create'} <= set(row['actions']) or not self.store.tenant(actor.tenant_id).get('calendar_policy'):
            raise DomainError('unconfigured', 503)
        if self.state != 'MOCK' and not self.live_writes_approved:
            raise DomainError('forbidden', 403)
        resources = {r['id']: r for r in self.service.resources(actor, identity)}
        if not resources.get(row['resource_ids'][0], {}).get('writable'):
            raise DomainError('forbidden', 403)
        with self.store.transaction():
            if self.service.row(actor, identity) != row:
                raise DomainError('conflict', 409)
            if any(a['status'] == 'pending' for a in self.store.list('approvals', actor.tenant_id)) or any(
                c.get('status') in ('active', 'connected', 'ringing') for c in self.store.list('call_sessions', actor.tenant_id)):
                raise DomainError('conflict', 409)
            if any(j.get('kind') == 'customer_calendar_create' and j['status'] in ('pending','running','uncertain')
                   for j in self.store.list('jobs', actor.tenant_id)):
                raise DomainError('delivery_unknown', 409)
            previous = self.store.find('operations_events', actor.tenant_id, 'customer-booking-binding')
            import copy
            values = {'kind': 'customer_booking_binding', 'active': True, 'subject': actor.subject, 'connection_id': identity,
                'calendar_policy': copy.deepcopy(self.store.tenant(actor.tenant_id)['calendar_policy']), 'timezone': self.store.tenant(actor.tenant_id)['timezone']}
            if previous:
                self.store.update('operations_events', actor.tenant_id, previous['id'], values)
            else:
                self.store.add('operations_events', actor.tenant_id, values, external_key='customer-booking-binding')
            row = self.store.update('operations_events', actor.tenant_id, identity, {
                'booking_enabled': True, 'revision': revision+1})
            self.store.audit(actor, 'connector:customer_booking_enabled', resource_id=identity)
        return self.service.project(row)

    def busy(self, actor, row, resource, start, end):
        token = self.service.token(actor, row['id'])
        response = ProviderAdapter('google', self.service.http).call(token, 'POST', 'freeBusy', json={
            'timeMin': start.isoformat(), 'timeMax': end.isoformat(),
            'timeZone': self.policy(actor.tenant_id)['timezone'], 'items': [{'id': resource}]})
        if response.status_code != 200:
            raise DomainError('provider_error', 502)
        calendar = response.json().get('calendars', {}).get(resource)
        if not calendar or calendar.get('errors') or not isinstance(calendar.get('busy'), list):
            raise DomainError('provider_error', 502)
        result = []
        try:
            for item in calendar['busy']:
                low = datetime.fromisoformat(item['start'].replace('Z', '+00:00'))
                high = datetime.fromisoformat(item['end'].replace('Z', '+00:00'))
                if low.tzinfo is None or high.tzinfo is None or high <= low:
                    raise ValueError()
                result.append((low, high))
        except (KeyError, TypeError, ValueError):
            raise DomainError('provider_error', 502) from None
        return result

    def available(self, tenant, starts_at, minutes, exclude=None):
        actor, row, resource = self.context(tenant)
        start = datetime.fromisoformat(starts_at)
        policy = self.policy(tenant)['calendar_policy']
        # Reuse local business policy and persisted slot reservations, never its
        # synthetic availability as a substitute for the provider FreeBusy query.
        if start.tzinfo is None or start < self.clock() + timedelta(minutes=policy.get('notice_minutes', 0)):
            return False
        if not MockCalendarProvider(self.store).available(tenant, starts_at, minutes, exclude, tenant_override=self.policy(tenant)):
            return False
        buffer = timedelta(minutes=policy.get('buffer_minutes', 0))
        low, high = start-buffer, start+timedelta(minutes=minutes)+buffer
        return not any(low < busy_end and busy_start < high for busy_start, busy_end in self.busy(actor, row, resource, low, high))

    def slots(self, tenant, day, minutes):
        actor, row, resource = self.context(tenant)
        zone = self.policy(tenant)['timezone']
        candidates = MockCalendarProvider(self.store).day_slots(tenant, day, minutes, zone, self.clock(), tenant_override=self.policy(tenant))
        if not candidates:
            return []
        policy = self.policy(tenant)['calendar_policy']
        buffer = timedelta(minutes=policy.get('buffer_minutes', 0))
        notice = self.clock() + timedelta(minutes=policy.get('notice_minutes', 0))
        starts = [datetime.fromisoformat(v) for v in candidates]
        busy = self.busy(actor, row, resource, min(starts)-buffer, max(starts)+timedelta(minutes=minutes)+buffer)
        return [value for value, start in zip(candidates, starts) if start >= notice and not any(
            start-buffer < high and low < start+timedelta(minutes=minutes)+buffer for low, high in busy)]

    def execute(self, principal, assistant, conversation, name, args, *, key, correlation_id, approved=False):
        from .tools import ToolOutcome
        from .saas_domain import UsageEvent, UNITS
        self.engine.tools.authorize(principal, assistant, name)
        cache_key=conversation['id']+':'+key
        with self.store.transaction():
            previous=self.store.find('tool_executions',principal.tenant_id,cache_key)
            if previous:
                return previous['outcome']
            if self.store.entitlements:
                for category in ('tool_executions','agent_executions'):
                    self.store.entitlements.record(principal.tenant_id,UsageEvent(resource_id=conversation['id'],category=category,quantity=1,unit=UNITS[category],provider='mock' if self.state=='MOCK' else 'google',timestamp=self.clock(),correlation_id=correlation_id,idempotency_key=cache_key+':'+category,billable=self.state!='MOCK'))
            outcome=ToolOutcome.model_validate(self._execute(principal,assistant,conversation,name,args,key=key,correlation_id=correlation_id,approved=approved)).model_dump()
            self.store.add('tool_executions',principal.tenant_id,{'conversation_id':conversation['id'],'agent':'executor','tool':name,'arguments':args,'outcome':outcome,'correlation_id':correlation_id,'approved_by':principal.user_id if approved else None,'timestamp':now()},external_key=cache_key)
            self.store.audit(principal,'tool:'+name,resource_id=conversation['id'],correlation_id=correlation_id)
            self.store.add('usage_records',principal.tenant_id,{'kind':'tool_execution','agent':'executor','tool':name,'billing_precharged':bool(self.store.entitlements),'channel':conversation['channel'],'correlation_id':correlation_id,'timestamp':now(),'price':None})
            return outcome

    def _execute(self, principal, assistant, conversation, name, args, *, key, correlation_id, approved=False):
        tenant = principal.tenant_id
        if name == 'CheckAvailability':
            if args.get('day'):
                slots = self.slots(tenant, args['day'], args['duration_minutes'])
                data = {'available': bool(slots), 'available_slots': slots, 'state': self.state}
            else:
                data = {'available': self.available(tenant, args['starts_at'], args['duration_minutes']), 'state': self.state}
            return {'status': 'completed', 'code': 'available' if data['available'] else 'unavailable', 'data': data}
        if name != 'CreateAppointment' or not approved:
            raise DomainError('forbidden', 403)
        actor, row, resource = self.context(tenant, write=True)
        fingerprint = sha256(str(sorted(args.items())).encode()).hexdigest()
        external_key = 'customer-booking:' + sha256((conversation['id'] + ':' + key).encode()).hexdigest()
        with self.store.transaction():
            previous = self.store.find('jobs', tenant, external_key)
            if previous:
                if previous['fingerprint'] != fingerprint:
                    raise DomainError('conflict', 409)
                appointment = self.store.get('appointments', tenant, previous['appointment_id'])
            else:
                if not self.available(tenant, args['starts_at'], args['duration_minutes']):
                    raise DomainError('conflict', 409)
                appointment = self.store.add('appointments', tenant, {**args,
                    'assistant_id': assistant['id'], 'conversation_id': conversation['id'],
                    'locale': conversation['active_locale'], 'timezone': self.policy(tenant)['timezone'],
                    'provider': 'customer_google', 'status': 'pending_external'})
                self.store.add('jobs', tenant, {'kind': 'customer_calendar_create', 'status': 'pending',
                    'appointment_id': appointment['id'], 'connection_id': row['id'], 'connection_revision': row['revision'],
                    'resource_id': row['resource_ids'][0], 'conversation_id': conversation['id'], 'assistant_id': assistant['id'],
                    'actor_subject': actor.subject, 'fingerprint': fingerprint, 'event_id': sha256(external_key.encode()).hexdigest(),
                    'correlation_id': correlation_id, 'due_at': self.clock().isoformat(), 'attempts': 0}, external_key=external_key)
            return {'status': 'completed', 'code': 'appointment_created' if appointment['status'] == 'confirmed' else 'appointment_pending',
                    'data': {**appointment, 'state': self.state}}

    def persist_confirmation(self, tenant, job, event):
        with self.store.transaction():
            current = self.store.get('jobs', tenant, job['id'])
            if current['status'] == 'completed':
                return
            if current.get('claim') != job.get('claim'):
                raise DomainError('conflict',409)
            appointment = self.store.get('appointments', tenant, job['appointment_id'])
            expected_start = datetime.fromisoformat(appointment['starts_at'])
            try:
                actual_start = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                actual_end = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
                if event.get('id') != job['event_id'] or event.get('status') == 'cancelled' or actual_start != expected_start or actual_end != expected_start+timedelta(minutes=appointment['duration_minutes']):
                    raise ValueError()
            except (ValueError, KeyError, TypeError):
                raise DomainError('delivery_unknown', 409) from None
            self.store.update('appointments', tenant, appointment['id'], {'status': 'confirmed',
                'google_event_id': job['event_id'], 'google_etag': event.get('etag')})
            locale = appointment['locale']
            text = tr(locale, 'appointment_created', date=format_date(appointment['starts_at'], locale, appointment['timezone']))
            # Web Chat reads persisted replies. Other channels need their existing
            # authorized outbox; no email/SIP/SMS provider is silently activated.
            conversation = self.store.get('conversations', tenant, job['conversation_id'])
            if conversation['channel'] == 'web_chat':
                self.store.add('messages', tenant, {'conversation_id': conversation['id'], 'assistant_id': job['assistant_id'],
                    'content': text, 'locale': locale, 'direction': 'outbound', 'status': 'sent', 'timestamp': now(),
                    'expires_at': (self.clock()+timedelta(days=self.store.tenant(tenant)['retention_days'])).isoformat(),
                    'metadata': {'agent': 'receptionist', 'kind': 'customer_booking_confirmation', 'appointment_id': appointment['id'], 'state': self.state}, 'channel': 'web_chat'},
                    external_key='customer-confirmation:' + job['id'])
            self.store.add('jobs', tenant, {'kind': 'appointment_reminder', 'status': 'pending',
                'appointment_id': appointment['id'], 'conversation_id': conversation['id'], 'attempts': 0,
                'due_at': (expected_start-timedelta(hours=1)).isoformat()}, external_key='reminder:' + appointment['id'])
            self.store.update('jobs', tenant, job['id'], {'status': 'completed', 'completed_at': now()})
            actor = self.store.principal(job['actor_subject'], tenant)
            self.store.audit(actor, 'connector:customer_booking_confirmed', resource_id=appointment['id'])

    def worker(self):
        # Called by the existing maintenance supervisor, outside request transactions.
        with self.store.lock:
            dynamic = [r[0] for r in self.store.db.execute(
                "SELECT DISTINCT tenant_id FROM operations_events WHERE json_extract(data,'$.kind')='customer_booking_binding' AND json_extract(data,'$.active')=1")]
        for tenant in set(self.bindings) | set(dynamic):
            for candidate in self.store.list('jobs', tenant):
                if candidate.get('kind') != 'customer_calendar_create' or candidate['status'] not in ('pending', 'running', 'uncertain'):
                    continue
                with self.store.transaction():
                    job = self.store.get('jobs', tenant, candidate['id'])
                    if job['status'] not in ('pending','running','uncertain'):
                        continue
                    recover = job['status'] in ('running', 'uncertain')
                    if job.get('lease_until') and datetime.fromisoformat(job['lease_until']) > self.clock():
                        continue
                    job=self.store.update('jobs', tenant, job['id'], {'status': 'running', 'claim': uid(),
                        'lease_until': (self.clock()+timedelta(seconds=60)).isoformat()})
                try:
                    actor, row, resource = self.context(tenant, write=True)
                    if row['id'] != job['connection_id'] or row['revision'] != job['connection_revision'] or row['resource_ids'][0] != job['resource_id']:
                        raise DomainError('disabled', 409)
                    appointment = self.store.get('appointments', tenant, job['appointment_id'])
                    assistant = self.store.get('assistants', tenant, job['assistant_id'])
                    conversation = self.store.get('conversations', tenant, job['conversation_id'])
                    if assistant['status'] != 'active' or conversation['channel'] not in assistant['enabled_channels'] or conversation.get('human_escalation'):
                        raise DomainError('disabled', 409)
                    self.engine.tools.authorize(actor, assistant, 'CreateAppointment')
                    adapter = ProviderAdapter('google', self.service.http)
                    token = self.service.token(actor, row['id'])
                    path = 'calendars/' + quote(resource, safe='') + '/events/' + job['event_id']
                    if recover:
                        response = adapter.call(token, 'GET', path)
                        if response.status_code != 200:
                            raise DomainError('delivery_unknown', 409)
                    else:
                        if not self.available(tenant, appointment['starts_at'], appointment['duration_minutes'], appointment['id']):
                            raise DomainError('conflict', 409)
                        # Linearize final write admission against revocation and
                        # competing claims. A later disconnect cannot undo an
                        # already admitted/in-flight HTTP write; retain its real
                        # receipt or uncertainty and never replay the POST.
                        with self.store.transaction():
                            fresh = self.store.get('jobs',tenant,job['id'])
                            if fresh.get('claim') != job['claim'] or fresh['status'] != 'running':
                                raise DomainError('delivery_unknown',409)
                            actor,row,resource = self.context(tenant,write=True)
                            if row['id'] != job['connection_id'] or row['revision'] != job['connection_revision'] or row['resource_ids'][0] != job['resource_id']:
                                raise DomainError('disabled',409)
                            assistant = self.store.get('assistants',tenant,job['assistant_id'])
                            conversation = self.store.get('conversations',tenant,job['conversation_id'])
                            if assistant['status'] != 'active' or conversation['channel'] not in assistant['enabled_channels'] or conversation.get('human_escalation'):
                                raise DomainError('disabled',409)
                            self.engine.tools.authorize(actor,assistant,'CreateAppointment')
                            token = self.service.token(actor,row['id'])
                            self.store.update('jobs',tenant,job['id'],{'write_admitted_at':self.clock().isoformat(),
                                'lease_until':(self.clock()+timedelta(seconds=60)).isoformat()})
                        start = datetime.fromisoformat(appointment['starts_at'])
                        response = adapter.call(token, 'POST', path.rsplit('/', 1)[0], params={'sendUpdates': 'none'}, json={
                            'id': job['event_id'], 'summary': 'Appointment',
                            'start': {'dateTime': start.isoformat(), 'timeZone': appointment['timezone']},
                            'end': {'dateTime': (start+timedelta(minutes=appointment['duration_minutes'])).isoformat(), 'timeZone': appointment['timezone']}})
                        if response.status_code == 409:
                            response = adapter.call(token, 'GET', path)
                        if response.status_code not in (200, 201):
                            raise DomainError('delivery_unknown', 409)
                    self.persist_confirmation(tenant, job, response.json())
                except DomainError as error:
                    uncertain = recover or error.code in ('delivery_unknown', 'provider_error', 'timeout', 'provider_rate_limited')
                    with self.store.transaction():
                        current=self.store.get('jobs',tenant,job['id'])
                        if current['status']=='completed' or current.get('claim') != job.get('claim'):
                            continue
                        self.store.update('jobs', tenant, job['id'], {'status': 'uncertain' if uncertain else 'blocked',
                            'failure_code': error.code, 'lease_until': (self.clock()+timedelta(seconds=60)).isoformat() if uncertain else None})
                        self.store.update('appointments', tenant, job['appointment_id'], {
                            'status': 'uncertain_external' if uncertain else 'cancelled', 'failure_code': error.code})
                        appointment=self.store.get('appointments',tenant,job['appointment_id'])
                        conversation=self.store.get('conversations',tenant,job['conversation_id'])
                        notice_key='customer-booking-notice:'+job['id']+':'+('uncertain' if uncertain else 'failed')
                        if conversation['channel']=='web_chat' and not self.store.find('messages',tenant,notice_key):
                            self.store.add('messages',tenant,{'conversation_id':conversation['id'],'assistant_id':job['assistant_id'],'content':tr(appointment['locale'],'customer_booking_uncertain' if uncertain else 'customer_booking_failed'),'locale':appointment['locale'],'direction':'outbound','status':'sent','timestamp':now(),'channel':'web_chat','expires_at':(self.clock()+timedelta(days=self.store.tenant(tenant)['retention_days'])).isoformat(),'metadata':{'agent':'receptionist','kind':'customer_booking_notice','appointment_id':appointment['id'],'final':not uncertain}},external_key=notice_key)


def register_customer_booking(app, bridge, actor):
    from fastapi import Depends
    from pydantic import Field
    from .domain import Contract, Principal
    class Enable(Contract):
        revision: int = Field(ge=1)
        confirmed: bool = False

    @app.post('/api/customer-connectors/connections/{identity}/booking/enable')
    def enable(identity: str, payload: Enable, principal: Principal = Depends(actor)):
        return bridge.configure(principal, identity, payload.revision, payload.confirmed)
