"""Persistent, channel-independent booking dialogue with two explicit agents."""
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pydantic import ValidationError
from .domain import (BookingInterpretationRequest, BookingIntent, BookingState, Handoff, DomainError)
from .language import parse_date, format_date, tr
from time import monotonic


def explicit_confirmation(text):
    """Application-owned consent gate; a provider's intent alone never authorizes a write."""
    import re
    if '?' in text: return False
    normalize=lambda value:' '.join(re.sub(r'[,.!]',' ',value.casefold()).split())
    return normalize(text) in {normalize(value) for value in {
        'yes', 'yes, confirm', 'yes confirm', 'confirm', 'i confirm',
        'да', 'да, потвърждавам', 'да потвърждавам', 'потвърждавам',
        'потвърждавам часа','да, потвърждавам часа','да потвърждавам часа',
        'да, потвърждавам часа за прегледа','да потвърждавам часа за прегледа',
        'да потвърждавам резервацията','потвърждавам резервацията',
        'точно така',
        'i confirm the appointment','yes, i confirm','yes i confirm',
        'yes, i confirm the appointment','yes i confirm the appointment'}}


def explicit_cancellation(text):
    """A model-only cancellation guess cannot discard an active proposal."""
    import re
    if '?' in text: return False
    value=' '.join(re.sub(r'[,.!]',' ',text.casefold()).split())
    return value in {'cancel','cancel booking','cancel the booking','please cancel','please cancel the booking',
        'no','no thanks','never mind','nevermind','do not book','do not confirm',
        'не','не благодаря','отказ','отказвам','отказвам часа','откажи','откажи часа','не потвърждавам','не записвай час'}


def pending_confirmation_decision(text):
    """Exact utterances, used only with a valid pending proposal, never fuzzy consent."""
    if explicit_confirmation(text): return 'confirm'
    if explicit_cancellation(text): return 'reject'
    if text.casefold().strip(' .!') in ('искам друг час', 'i want another time', 'a different time please'):
        return 'change'
    return 'unclear'


class ReceptionistAgent:
    def __init__(self, provider):
        self.provider = provider

    def interpret(self, text, locale, *, collecting_name=False, provider=None, context=None):
        request = BookingInterpretationRequest(content=text, locale=locale, collecting_name=collecting_name, context=context or {})
        try:
            return BookingIntent.model_validate((provider or self.provider).interpret_booking(request))
        except (ValidationError, TypeError, AttributeError):
            raise DomainError('provider_error', 502) from None

    def outcome_reply(self, outcome, locale, timezone, tools, tenant_id):
        return tools.localized(outcome, locale, timezone, tenant_id)


class TaskExecutionAgent:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.store, self.tools = orchestrator.store, orchestrator.tools

    def handoff(self, principal, assistant, conversation, tool, arguments, locale, correlation, *, phase='execution', provider=None):
        if 'executor' not in assistant['assigned_agents']:
            raise DomainError('disabled', 409)
        self.tools.authorize(principal, assistant, tool)
        arguments = self.tools.validate(tool, arguments)
        if provider and 'validated_tools' in provider.capability.features:
            from .tools import SCHEMAS
            proposed = self.tools.validate(tool, provider.propose_tool(tool, arguments, SCHEMAS[tool].model_json_schema()))
            provider.check_cancelled()
            if proposed != arguments: raise DomainError('invalid_model_output', 502)
            self.tools.authorize(principal, assistant, tool)
        handoff = Handoff(tenant_id=principal.tenant_id, conversation_id=conversation['id'], intent=tool,
                          arguments=arguments, locale=locale, correlation_id=correlation, assistant_id=assistant['id'],
                          contact_id=conversation.get('contact_id'), call_session_id=conversation.get('call_session_id'),
                          tool_permissions=assistant['allowed_tools'])
        self.orchestrator.validate_handoff(handoff, principal, steps=1, depth=1, tool_calls=1)
        if tool == 'CreateAppointment' and phase == 'execution' and self.store.operations:
            from .observability import correlation_id
            self.store.operations.trace_voice(principal.tenant_id, 'agent_authorized', correlation_id.get() or correlation,
                call_id=conversation.get('call_session_id'), conversation_id=conversation['id'],
                parent_correlation_id=correlation)
        self.store.add('agent_executions', principal.tenant_id, {
            'conversation_id': conversation['id'], 'handoff': handoff.model_dump(),
            'status': 'delegated', 'phase': phase, 'workflow': 'booking', 'timestamp': self.orchestrator.clock().isoformat()})
        return arguments

    def check(self, principal, assistant, conversation, state, event_id, correlation, provider=None):
        arguments = self.handoff(principal, assistant, conversation, 'CheckAvailability', {
            'starts_at': state.starts_at, 'duration_minutes': state.duration_minutes}, state.locale, correlation, provider=provider)
        return self.tools.execute(principal, assistant, conversation, 'CheckAvailability', arguments,
                                  key='booking:availability:' + event_id, correlation_id=correlation)

    def propose(self, principal, assistant, conversation, state, correlation, provider=None):
        arguments = self.handoff(principal, assistant, conversation, 'CreateAppointment', {
            'starts_at': state.starts_at, 'duration_minutes': state.duration_minutes,
            'contact_name': state.contact_name}, state.locale, correlation, phase='proposal', provider=provider)
        return self.store.add('approvals', principal.tenant_id, {
            'conversation_id': conversation['id'], 'assistant_id': assistant['id'],
            'tool': 'CreateAppointment', 'arguments': arguments, 'locale': state.locale,
            'correlation_id': correlation, 'requested_by': principal.user_id, 'status': 'pending',
            'workflow': 'booking', 'timezone': state.timezone, 'reference_at': state.reference_at.isoformat(),
            'expires_at': (self.orchestrator.clock() + timedelta(minutes=15)).isoformat(),
            'fingerprint': sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest()})


class BookingWorkflow:
    def __init__(self, orchestrator):
        self.orchestrator, self.store = orchestrator, orchestrator.store
        self.receptionist = ReceptionistAgent(orchestrator.providers.llm)
        self.executor = TaskExecutionAgent(orchestrator)

    def save(self, principal, conversation, state):
        self.store.update('conversations', principal.tenant_id, conversation['id'],
                          {'booking_state': state.model_dump(mode='json')})

    def summary(self, state):
        return tr(state.locale, 'booking_confirm', date=format_date(state.starts_at, state.locale, state.timezone),
                  name=state.contact_name, duration=state.duration_minutes)

    def cancel_previous(self, principal, state):
        if state.approval_id:
            approval = self.store.get('approvals', principal.tenant_id, state.approval_id)
            if approval['status'] == 'pending':
                self.store.update('approvals', principal.tenant_id, state.approval_id, {'status': 'cancelled'})
            state.approval_id = None

    def handle(self, principal, assistant, conversation, incoming, locale, correlation, received_at, provider=None, reference_at=None):
        raw = conversation.get('booking_state')
        state = BookingState.model_validate(raw) if raw else None
        started = monotonic()
        decision = pending_confirmation_decision(incoming.content) if state and state.status == 'awaiting_confirmation' else None
        if self.store.operations and conversation['channel'] == 'voice':
            self.store.operations.trace_voice(principal.tenant_id, 'pending_state', correlation,
                call_id=conversation.get('call_session_id'), conversation_id=conversation['id'], state=state.status if state else 'none')
        if state and state.status == 'awaiting_confirmation':
            approval = self.store.get('approvals', principal.tenant_id, state.approval_id)
            if approval['status'] != 'pending' or datetime.fromisoformat(approval['expires_at']) <= received_at:
                if conversation['channel'] != 'voice':
                    raise DomainError('expired', 409)
                self.cancel_previous(principal, state)
                state.status, state.locale = 'cancelled', locale
                self.save(principal, conversation, state)
                if self.store.operations:
                    self.store.operations.trace_voice(principal.tenant_id, 'confirmation_evaluated', correlation,
                        call_id=conversation.get('call_session_id'), decision='expired', intent_source='pending_state')
                return {'response': tr(locale, 'expired'), 'booking_status': state.status}
            if decision == 'change':
                self.cancel_previous(principal, state)
                state.status, state.starts_at, state.requested_day, state.locale = 'need_date', None, None, locale
                self.save(principal, conversation, state)
                if self.store.operations:
                    self.store.operations.trace_voice(principal.tenant_id, 'confirmation_evaluated', correlation,
                        call_id=conversation.get('call_session_id'), decision='change', intent_source='literal_pending')
                return {'response': tr(locale, 'booking_date'), 'booking_status': state.status}
        # A valid pending proposal supplies context; literal consent does not need
        # a second probabilistic intent veto. Tool authorization still runs below.
        if decision in ('confirm', 'reject'):
            intent = BookingIntent(intent='confirm' if decision == 'confirm' else 'cancel')
        elif state and state.status == 'completed' and explicit_confirmation(incoming.content):
            intent = BookingIntent(intent='confirm')
        else:
            intent = self.receptionist.interpret(incoming.content, locale,
                                            collecting_name=bool(state and state.status == 'need_name'), provider=provider,
                                            context=state.model_dump(mode='json') if state else {})
        if self.store.operations and conversation['channel'] == 'voice' and decision:
            self.store.operations.trace_voice(principal.tenant_id, 'confirmation_evaluated', correlation,
                call_id=conversation.get('call_session_id'), conversation_id=conversation['id'],
                decision=decision, intent_source='literal_pending' if decision in ('confirm','reject') else 'llm',
                **({'provider_intent':intent.intent} if decision not in ('confirm','reject') else {}),
                duration_ms=round((monotonic()-started)*1000, 3))
            self.store.operations.observe('confirmation_processing', principal.tenant_id, duration_ms=(monotonic()-started)*1000)
        active = state and state.status not in ('completed', 'cancelled')
        if not active and intent.intent != 'book':
            if state and state.status == 'completed' and intent.intent == 'confirm' and state.approval_id:
                previous = self.store.get('approvals', principal.tenant_id, state.approval_id)['result']
                state.locale = locale
                self.save(principal, conversation, state)
                return {**previous, 'locale': locale, 'booking_status': 'completed',
                        'response': self.receptionist.outcome_reply(previous['outcome'], locale, state.timezone,
                                                                  self.orchestrator.tools, principal.tenant_id)}
            return None
        if state is None or not active:
            state = BookingState(status='need_date', reference_at=reference_at or received_at,
                                 timezone=self.store.tenant(principal.tenant_id)['timezone'],
                                 duration_minutes=assistant.get('booking_duration_minutes', 30), locale=locale)
        state.locale = locale
        if intent.intent == 'cancel':
            if not explicit_cancellation(incoming.content):
                state.locale = locale
                self.save(principal, conversation, state)
                return {'response':tr(locale,'booking_confirmation_unclear'),'booking_status':state.status,'confirmation_unclear':True}
            self.cancel_previous(principal, state)
            state.status = 'cancelled'
            self.save(principal, conversation, state)
            return {'response': tr(locale, 'booking_cancelled'), 'booking_status': state.status}
        if state.status == 'awaiting_confirmation' and intent.intent == 'confirm' and explicit_confirmation(incoming.content):
            approval = self.store.get('approvals', principal.tenant_id, state.approval_id)
            if approval['locale'] != locale:
                self.store.update('approvals', principal.tenant_id, approval['id'], {'locale': locale})
            self.executor.handoff(principal, assistant, conversation, 'CreateAppointment', approval['arguments'], locale, approval['correlation_id'], provider=provider)
            self.save(principal, conversation, state)
            result = self.orchestrator.approve(principal, state.approval_id)
            return {**result, 'already_dispatched': True, 'booking_status': 'completed'}
        changed = False
        if intent.day_text:
            day = parse_date(intent.day_text + ' 09:00', locale, state.timezone, reference=state.reference_at)
            state.requested_day = day.date().isoformat()
            if not intent.date_text:
                arguments = self.executor.handoff(principal, assistant, conversation, 'CheckAvailability',
                    {'day': state.requested_day, 'duration_minutes': state.duration_minutes}, locale, correlation, provider=provider)
                outcome = self.orchestrator.tools.execute(principal, assistant, conversation, 'CheckAvailability', arguments,
                    key='booking:day:' + incoming.event_id, correlation_id=correlation)
                self.save(principal, conversation, state)
                label = day.strftime('%d.%m.%Y' if locale == 'bg-BG' else '%m/%d/%Y') + ' ' + state.timezone
                return {'response': tr(locale, 'booking_day', date=label) if outcome['data']['available'] else tr(locale, 'booking_unavailable'),
                        'booking_status': 'need_date', 'outcome': outcome}
        if intent.date_text:
            try:
                value = state.requested_day + 'T' + intent.date_text if state.requested_day and len(intent.date_text) <= 5 else intent.date_text
                parsed = parse_date(value, locale, state.timezone, reference=state.reference_at)
            except DomainError:
                # Ask for an unambiguous date instead of guessing or abandoning the dialogue.
                self.cancel_previous(principal, state)
                state.status, state.starts_at = 'need_date', None
                self.save(principal, conversation, state)
                return {'response': tr(locale, 'booking_date'), 'booking_status': 'need_date'}
            if parsed < received_at:
                self.cancel_previous(principal, state)
                state.status, state.starts_at = 'need_date', None
                self.save(principal, conversation, state)
                return {'response': tr(locale, 'booking_future'), 'booking_status': 'need_date'}
            value = parsed.isoformat()
            changed = value != state.starts_at
            state.starts_at = value
        if intent.duration_minutes is not None:
            changed = changed or intent.duration_minutes != state.duration_minutes
            state.duration_minutes = intent.duration_minutes
        if intent.contact_name:
            changed = changed or intent.contact_name != state.contact_name
            state.contact_name = intent.contact_name
        if changed:
            self.cancel_previous(principal, state)
        if state.status == 'awaiting_confirmation' and not changed:
            approval = self.store.update('approvals', principal.tenant_id, state.approval_id, {'locale': locale})
            self.save(principal, conversation, state)
            return {'response': tr(locale, 'booking_confirmation_unclear') + ' ' + self.summary(state), 'approval': approval, 'booking_status': state.status, 'confirmation_unclear':True}
        if state.starts_at is None:
            state.status = 'need_date'
            response = tr(locale, 'booking_date')
            outcome, approval = None, None
        else:
            outcome = self.executor.check(principal, assistant, conversation, state, incoming.event_id, correlation, provider=provider)
            if not outcome['data']['available']:
                state.status = 'unavailable'
                response, approval = tr(locale, 'booking_unavailable'), None
                if outcome['data'].get('available_slots'):
                    slots = ', '.join(format_date(slot, locale, state.timezone) for slot in outcome['data']['available_slots'])
                    response += ' ' + tr(locale, 'booking_alternatives', slots=slots)
            elif state.contact_name is None:
                state.status = 'need_name'
                response = tr(locale, 'booking_name', date=format_date(state.starts_at, locale, state.timezone), duration=state.duration_minutes)
                approval = None
            else:
                approval = self.executor.propose(principal, assistant, conversation, state, correlation, provider=provider)
                state.approval_id, state.status = approval['id'], 'awaiting_confirmation'
                response = self.summary(state)
        self.save(principal, conversation, state)
        return {'response': response, 'approval': approval, 'outcome': outcome,
                'booking_status': state.status, 'reference_at': state.reference_at.isoformat()}
