"""Validated, permission-checked mock business actions and auditable outcomes."""
from datetime import datetime, timedelta, timezone
from time import monotonic
from pydantic import BaseModel, ConfigDict, ValidationError
from .domain import (AppointmentArgs, AppointmentId, RescheduleArgs, AvailabilityArgs,
                     SendArgs, FollowUpArgs, EscalationArgs, DomainError, Message)
from .language import format_date, tr
from .store import uid, now
from .providers import e164, sms_segments
from .saas_domain import UsageEvent, UNITS
from .observability import timed


class ToolOutcome(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: str
    code: str
    data: dict


SCHEMAS = {
    'CheckAvailability': AvailabilityArgs, 'CreateAppointment': AppointmentArgs,
    'RescheduleAppointment': RescheduleArgs, 'CancelAppointment': AppointmentId,
    'SendMessage': SendArgs, 'CreateFollowUpTask': FollowUpArgs, 'EscalateToHuman': EscalationArgs,
}


class ToolRegistry:
    def __init__(self, store, providers, clock=None):
        self.store, self.providers = store, providers
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.messaging = None
        self.extensions = {}
        providers.configure_calendar(store)

    def describe(self):
        return [{'name': name, 'description_key': name, 'input_schema': schema.model_json_schema(),
                 'output_schema': ToolOutcome.model_json_schema(), 'timeout_seconds': 90 if name in self.extensions else 5,
                 'confirmation_policy': 'none' if name in ('CheckAvailability','ConciergeAvailability') else 'explicit',
                 'idempotency': 'tenant_conversation_action', 'state': getattr(self.extensions.get(name), 'state', 'LIVE_UNVERIFIED') if name in self.extensions else 'MOCK'} for name, schema in SCHEMAS.items()]

    def validate(self, name, arguments):
        if name not in SCHEMAS:
            raise DomainError('tool_denied', 403)
        try:
            return SCHEMAS[name].model_validate(arguments).model_dump(mode='json')
        except ValidationError:
            raise DomainError('invalid_input', 422) from None

    def authorize(self, principal, assistant, name):
        principal.require('execute')
        agent = self.store.get('agents', principal.tenant_id, 'executor')
        if name not in assistant['allowed_tools'] or name not in agent['allowed_tools'] or not agent['enabled']:
            raise DomainError('tool_denied', 403)

    def available(self, tenant_id, starts_at, minutes, exclude=None):
        return self.providers.calendar.available(tenant_id, starts_at, minutes, exclude)

    @timed('tool_execution')
    def execute(self, principal, assistant, conversation, name, arguments, *, key, correlation_id, approved=False):
        self.authorize(principal, assistant, name)
        args = self.validate(name, arguments)
        if name != 'CheckAvailability' and not approved:
            if name=='ConciergeAvailability':pass
            else:raise DomainError('forbidden', 403)
        if name in self.extensions and (not hasattr(self.extensions[name], 'supports') or self.extensions[name].supports(principal.tenant_id)):
            return self.extensions[name].execute(principal,assistant,conversation,name,args,key=key,correlation_id=correlation_id,approved=approved)
        if name.startswith('Concierge'):
            raise DomainError('unconfigured',503)
        cache_key = conversation['id'] + ':' + key
        with self.store.transaction():
            previous = self.store.find('tool_executions', principal.tenant_id, cache_key)
            if previous:
                return previous['outcome']
            if self.store.entitlements:
                for category in ('tool_executions', 'agent_executions'):
                    self.store.entitlements.record(principal.tenant_id, UsageEvent(resource_id=conversation['id'], category=category, quantity=1,
                        unit=UNITS[category], provider='mock', timestamp=self.clock(), correlation_id=correlation_id,
                        idempotency_key=cache_key + ':' + category))
            start = monotonic()
            outcome = self._run(principal, assistant, conversation, name, args)
            if monotonic() - start > 5:
                raise DomainError('timeout', 504)
            outcome = ToolOutcome.model_validate(outcome).model_dump()
            self.store.add('tool_executions', principal.tenant_id, {
                'conversation_id': conversation['id'], 'agent': 'executor', 'tool': name,
                'arguments': args, 'outcome': outcome, 'correlation_id': correlation_id,
                'approved_by': principal.user_id if approved else None, 'timestamp': now()}, external_key=cache_key)
            self.store.audit(principal, 'tool:' + name, correlation_id=correlation_id, resource_id=conversation['id'])
            self.store.add('usage_records', principal.tenant_id, {'kind': 'tool_execution', 'agent': 'executor', 'tool': name,
                'billing_precharged': bool(self.store.entitlements),
                'channel': conversation['channel'], 'correlation_id': correlation_id, 'timestamp': now(), 'price': None})
            return outcome

    def _run(self, principal, assistant, conversation, name, args):
        tenant_id = principal.tenant_id
        data, code = {}, 'completed'
        if name in ('CheckAvailability', 'CreateAppointment', 'RescheduleAppointment'):
            if name == 'CheckAvailability' and args.get('day'):
                zone = self.store.tenant(tenant_id)['timezone']
                slots = self.providers.calendar.day_slots(tenant_id, args['day'], args['duration_minutes'], zone, self.clock())
                return {'status': 'completed', 'code': 'available' if slots else 'unavailable',
                    'data': {'available': bool(slots), 'available_slots': slots, 'day': args['day'], 'timezone': zone, 'state': 'MOCK'}}
            start = datetime.fromisoformat(args['starts_at'])
            if start < self.clock():
                raise DomainError('invalid_input', 422)
            if name == 'RescheduleAppointment':
                original = self.store.get('appointments', tenant_id, args['appointment_id'])
                if original.get('provider') in ('google','customer_google'):raise DomainError('tool_denied',403)
                if original['status'] == 'cancelled':
                    raise DomainError('conflict', 409)
            free = self.available(tenant_id, args['starts_at'], args['duration_minutes'], args.get('appointment_id'))
            if name == 'CheckAvailability':
                data = {'available': free}
                if not free:
                    from zoneinfo import ZoneInfo
                    zone = self.store.tenant(tenant_id)['timezone']
                    day = start.astimezone(ZoneInfo(zone)).date().isoformat()
                    data['available_slots'] = self.providers.calendar.day_slots(tenant_id, day, args['duration_minutes'], zone, self.clock())[:3]
                return {'status': 'completed', 'code': 'available' if free else 'unavailable', 'data': data}
            if not free:
                raise DomainError('conflict', 409)
            if name == 'CreateAppointment':
                data = self.providers.calendar.create(tenant_id, args, conversation, self.store.tenant(tenant_id)['timezone'])
                code = 'appointment_created'
            else:
                data = self.providers.calendar.reschedule(tenant_id, args['appointment_id'], {k: v for k, v in args.items() if k != 'appointment_id'})
                if self.messaging: self.messaging.cancel_obsolete(tenant_id, args['appointment_id'], data['starts_at'])
                code = 'appointment_rescheduled'
            due_at = (datetime.fromisoformat(args['starts_at']) - timedelta(hours=1)).isoformat()
            job_key = 'reminder:' + data['id']
            existing_job = self.store.find('jobs', tenant_id, job_key)
            if existing_job:
                self.store.update('jobs', tenant_id, existing_job['id'], {'due_at': due_at, 'status': 'pending', 'attempts': 0})
            else:
                self.store.add('jobs', tenant_id, {'appointment_id': data['id'], 'conversation_id': conversation['id'],
                               'due_at': due_at, 'status': 'pending', 'attempts': 0, 'kind': 'appointment_reminder'}, external_key=job_key)
        elif name == 'CancelAppointment':
            if self.store.get('appointments',tenant_id,args['appointment_id']).get('provider') in ('google','customer_google'):raise DomainError('tool_denied',403)
            data = self.providers.calendar.cancel(tenant_id, args['appointment_id'])
            if self.messaging: self.messaging.cancel_obsolete(tenant_id, args['appointment_id'])
            code = 'appointment_cancelled'
        elif name == 'CreateFollowUpTask':
            data = self.store.add('follow_up_tasks', tenant_id, {**args, 'status': 'open', 'locale': conversation['active_locale']})
        elif name == 'EscalateToHuman':
            data = self.store.add('follow_up_tasks', tenant_id, {'title': args['reason'], 'status': 'human_requested',
                                  'locale': conversation['active_locale'], 'conversation_id': conversation['id']})
            self.store.update('conversations', tenant_id, conversation['id'], {'human_escalation': True})
            code = 'escalated'
        elif name == 'SendMessage':
            if self.messaging and conversation.get('connection_id'):
                if args['channel'] != conversation['channel'] or args['recipient'] != conversation['remote_sender_id']:
                    raise DomainError('forbidden', 403)
                data = self.messaging.queue_response(principal, assistant, conversation, args['content'], conversation['active_locale'], uid(), force_approved=True)
                return {'status': 'completed', 'code': 'completed', 'data': data}
            category = {'sms': 'sms_segments', 'email': 'email_messages', 'whatsapp': 'whatsapp_messages'}.get(args['channel'])
            if self.store.entitlements and category:
                self.store.entitlements.check(tenant_id, category, sms_segments(args['content'])['segments'] if args['channel'] == 'sms' else 1)
            if args['channel'] not in assistant['enabled_channels']:
                raise DomainError('disabled', 409)
            if args['channel'] == 'sms':
                args['recipient'] = e164(args['recipient'])
                contact = self.store.find('contacts', tenant_id, args['recipient'])
                if contact and contact.get('sms_opt_out'):
                    raise DomainError('forbidden', 403)
            # The registry dispatches synthetic messages only. Out-of-window WhatsApp
            # needs an independently configured approved template, never an LLM assertion.
            message = Message(id=uid(), tenant_id=tenant_id, assistant_id=assistant['id'],
                              conversation_id=conversation['id'], channel=args['channel'], external_id=uid(),
                              sender='assistant', recipient=args['recipient'], content=args['content'],
                              locale=conversation['active_locale'], timestamp=datetime.now(timezone.utc), status='pending')
            data = self.providers.channels[args['channel']].send(message)
            self.store.add('messages', tenant_id, {**message.model_dump(mode='json'), 'direction': 'outbound', 'delivery': data}, id=message.id)
            self.store.add('usage_records', tenant_id, {'channel': args['channel'], 'messages': 1,
                           'kind': 'outbound_message', 'message_id': message.id,
                           'segments': data.get('segments', 0), 'cost_units': data.get('cost_units', 0),
                           'price': None, 'provider': 'mock', 'timestamp': now()})
        return {'status': 'completed', 'code': code, 'data': data}

    def localized(self, outcome, locale, timezone, tenant_id=None):
        args = {}
        if outcome['code'] in ('appointment_created', 'appointment_rescheduled'):
            args['date'] = format_date(outcome['data']['starts_at'], locale, timezone)
        if tenant_id:
            template = self.store.find('notification_templates', tenant_id, locale + ':' + outcome['code'])
            if template:
                return template['body'].format(**args)
        return tr(locale, outcome['code'], **args)
