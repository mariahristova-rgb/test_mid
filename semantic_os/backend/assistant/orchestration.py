"""One authorized gateway for all channels and both agents.

Natural-language suggestions and structured requests both use validated, authorized tools.
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from .domain import DomainError, Handoff, Message, Incoming, AssistantConfig
from .language import LanguageResolver, tr
from .store import uid, now, event_key
from .tools import ToolRegistry
from .booking import BookingWorkflow
from .observability import timed, correlation_id as request_correlation
from .saas_domain import UsageEvent, UNITS
from .providers import sms_segments


class Orchestrator:
    def __init__(self, store, providers, clock=None):
        self.store, self.providers = store, providers
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.tools = ToolRegistry(store, providers, clock=self.clock)
        self.languages = LanguageResolver()
        self.booking = BookingWorkflow(self)
        self.messaging = None

    def configuration(self, principal, conversation):
        assistant = self.store.get('assistants', principal.tenant_id, conversation['assistant_id'])
        snapshot = conversation.get('widget_snapshot_id')
        if snapshot:
            version = self.store.get('operations_events', principal.tenant_id, snapshot)
            if (version.get('kind') != 'widget_version' or version.get('assistant_id') != assistant['id']
                    or version.get('integration_id') != conversation.get('widget_integration_id')):
                raise DomainError('forbidden', 403)
            if assistant['status'] != 'active': raise DomainError('disabled', 409)
            return {**AssistantConfig.model_validate(version['config']).model_dump(mode='json'),
                'id': assistant['id'], 'tenant_id': principal.tenant_id}
        return assistant

    def conversation(self, principal, assistant_id, channel='web_chat', contact_id=None):
        principal.require('execute')
        if self.store.entitlements: self.store.entitlements.access(principal.tenant_id)
        assistant = self.store.get('assistants', principal.tenant_id, assistant_id)
        if assistant['status'] != 'active' or channel not in assistant['enabled_channels']:
            raise DomainError('disabled', 409)
        if contact_id:
            self.store.get('contacts', principal.tenant_id, contact_id)
        return self.store.add('conversations', principal.tenant_id, {'assistant_id': assistant_id, 'channel': channel,
                             'contact_id': contact_id, 'active_locale': None, 'status': 'open', 'human_escalation': False})

    @timed('agent_execution')
    def inbound(self, principal, conversation_id, incoming: Incoming, *, sender='user', recipient='assistant', attachments=None, message_context=None):
        principal.require('execute')
        with self.store.transaction():
            conversation = self.store.get('conversations', principal.tenant_id, conversation_id)
            assistant = self.configuration(principal, conversation)
            context = {**conversation, 'active_locale': conversation.get('active_locale') or assistant['default_locale']}
            correlation = request_correlation.get() or uid()
            with self.providers.llm_session(assistant, context, principal, self.store, correlation) as provider:
                result = self._inbound(principal, conversation_id, incoming, sender=sender, recipient=recipient,
                    attachments=attachments, message_context=message_context, provider=provider, correlation=correlation)
                if hasattr(provider, 'check_cancelled'): provider.check_cancelled()
                return result

    def _inbound(self, principal, conversation_id, incoming, *, sender, recipient, attachments, message_context, provider, correlation):
        principal.require('execute')
        with self.store.transaction():
            conversation = self.store.get('conversations', principal.tenant_id, conversation_id)
            if conversation['status'] == 'closed':
                raise DomainError('disabled', 409)
            assistant = self.configuration(principal, conversation)
            stop = conversation['channel'] == 'sms' and incoming.content.strip().casefold() in ('stop', 'stop all', 'unsubscribe', 'end', 'quit', 'cancel', 'отказ', 'спри', 'стоп')
            if not stop and (assistant['status'] != 'active' or conversation['channel'] not in assistant['enabled_channels']):
                raise DomainError('disabled', 409)
            key = event_key(conversation['channel'], incoming.event_id)
            existing = self.store.find('provider_events', principal.tenant_id, key)
            if existing:
                fingerprint = sha256(incoming.model_dump_json().encode()).hexdigest()
                if existing['conversation_id'] != conversation_id or existing.get('fingerprint') != fingerprint:
                    raise DomainError('conflict', 409)
                return {**existing['result'], 'duplicate': True}
            tenant = self.store.tenant(principal.tenant_id)
            subscription = self.store.entitlements.subscription(principal.tenant_id) if self.store.entitlements else None
            if not stop and not subscription and self.store.count('usage_records', principal.tenant_id) >= tenant['usage_limit']:
                raise DomainError('limit_reached', 429)
            contact = self.store.get('contacts', principal.tenant_id, conversation['contact_id']) if conversation.get('contact_id') else {}
            resolution = self.languages.resolve(incoming.content, explicit=incoming.locale, contact=contact.get('preferred_locale'),
                                                conversation=conversation.get('active_locale'), assistant=assistant['default_locale'],
                                                tenant=tenant['default_locale'])
            locale = resolution.locale
            if resolution.source == 'explicit' and contact:
                self.store.update('contacts', principal.tenant_id, contact['id'], {'preferred_locale': locale})
            context = message_context or {}
            received_at = context.get('timestamp', self.clock())
            for attachment_id in incoming.attachment_ids:
                item = self.store.get('attachments', principal.tenant_id, attachment_id)
                if item['conversation_id'] != conversation_id or item.get('redacted') or datetime.fromisoformat(item['expires_at']) <= self.clock():
                    raise DomainError('forbidden', 403)
                attachments = [*(attachments or []), {k: item[k] for k in ('name', 'media_type', 'size')} | {'storage_key': item['id']}]
            conversation = self.store.update('conversations', principal.tenant_id, conversation_id, {'active_locale': locale, 'last_inbound_at': received_at.isoformat()})
            message = Message(id=uid(), tenant_id=principal.tenant_id, assistant_id=assistant['id'],
                              conversation_id=conversation_id, channel=conversation['channel'], external_id=context.get('external_id', incoming.event_id),
                              provider=context.get('provider', 'mock'), metadata=context.get('metadata', {}),
                              sender=sender, recipient=recipient, content=incoming.content,
                              attachments=attachments or [], locale=locale, timestamp=received_at)
            self.store.add('messages', principal.tenant_id, {**message.model_dump(mode='json'), 'direction': 'inbound',
                           'detected_locale': self.languages.detect(incoming.content)[0],
                           'expires_at': (self.clock() + timedelta(days=tenant['retention_days'])).isoformat()}, id=message.id)
            self.store.update('messages', principal.tenant_id, message.id, {'correlation_id': correlation, 'active_locale': locale})
            result = {'locale': locale, 'resolution': resolution.__dict__, 'correlation_id': correlation,
                      'approval': None, 'outcome': None, 'state': 'MOCK', 'duplicate': False}
            if not stop and conversation.get('human_escalation') and (conversation.get('connection_id') or conversation.get('assigned_agent') == 'human'):
                result.update(response=None, delivery=None, paused=True)
                self.store.add('provider_events', principal.tenant_id, {'conversation_id': conversation_id, 'result': result,
                    'fingerprint': sha256(incoming.model_dump_json().encode()).hexdigest()}, external_key=key)
                self.store.audit(principal, 'message:received_while_paused', resource_id=conversation_id)
                return result
            if not stop:
                if self.store.entitlements:
                    for category in ('ai_messages', 'agent_executions'):
                        self.store.entitlements.record(principal.tenant_id, UsageEvent(resource_id=message.id, category=category, quantity=1,
                            unit=UNITS[category], provider='mock', timestamp=self.clock(), correlation_id=correlation,
                            idempotency_key=message.id + ':' + category))
                self.providers.require(assistant['llm_provider'], locale)
                agent = self.store.get('agents', principal.tenant_id, 'receptionist')
                if not agent['enabled'] or 'receptionist' not in assistant['assigned_agents']:
                    raise DomainError('disabled', 409)
            if stop: response = tr(locale, 'opted_out')
            elif 'structured_intents' not in provider.capability.features:
                from contextlib import nullcontext
                with self.store.operations.span('llm_provider', principal.tenant_id) if self.store.operations else nullcontext():
                    response = provider.reply(incoming.content, locale, assistant['instructions'])
            else: response = None
            faq_answered = False
            for faq in assistant.get('faq_entries', []):
                if incoming.content.strip().casefold() in (faq['question_bg'].casefold(), faq['question_en'].casefold()):
                    response = faq['answer_bg' if locale == 'bg-BG' else 'answer_en']
                    faq_answered = True
                    break
            if conversation['channel'] == 'sms' and stop:
                if not contact:
                    contact = self.store.add('contacts', principal.tenant_id, {'name': sender, 'address': sender,
                                             'preferred_locale': locale, 'sms_opt_out': True}, external_key=sender)
                    self.store.update('conversations', principal.tenant_id, conversation_id, {'contact_id': contact['id']})
                else:
                    self.store.update('contacts', principal.tenant_id, contact['id'], {'sms_opt_out': True})
                response = tr(locale, 'opted_out')
            elif self.messaging and conversation['channel'] != 'voice' and not assistant.get('escalation_rules', {}).get('keywords') and any(phrase in incoming.content.casefold() for phrase in
                    ('human operator', 'speak to a human', 'talk to a human', 'human please', 'човек', 'оператор')):
                self.tools.authorize(principal, assistant, 'EscalateToHuman')
                handoff = Handoff(tenant_id=principal.tenant_id, assistant_id=assistant['id'], conversation_id=conversation_id,
                    contact_id=conversation.get('contact_id'), intent='EscalateToHuman', arguments={'reason': incoming.content[:500]},
                    locale=locale, correlation_id=correlation, tool_permissions=assistant['allowed_tools'])
                self.validate_handoff(handoff, principal, steps=1, depth=1, tool_calls=1)
                self.store.add('agent_executions', principal.tenant_id, {'conversation_id': conversation_id, 'handoff': handoff.model_dump(), 'status': 'delegated'})
                outcome = self.tools.execute(principal, assistant, conversation, 'EscalateToHuman', {'reason': incoming.content[:500]},
                    key=incoming.event_id, correlation_id=correlation, approved=True)
                result['outcome'] = outcome
                self.messaging.human_control(principal, conversation_id, 'takeover')
                response = tr(locale, 'human_escalation')
            elif incoming.tool:
                if conversation.get('human_escalation') and assistant.get('escalation_rules', {}).get('pause_automation', True):
                    raise DomainError('disabled', 409)
                if 'executor' not in assistant['assigned_agents']:
                    raise DomainError('disabled', 409)
                self.tools.authorize(principal, assistant, incoming.tool)
                arguments = self.booking.executor.handoff(principal, assistant, conversation, incoming.tool,
                    incoming.arguments, locale, correlation, provider=provider)
                handoff = Handoff(tenant_id=principal.tenant_id, conversation_id=conversation_id,
                                  intent=incoming.tool, arguments=arguments, locale=locale, correlation_id=correlation,
                                  assistant_id=assistant['id'], contact_id=conversation.get('contact_id'),
                                  call_session_id=conversation.get('call_session_id'), tool_permissions=assistant['allowed_tools'])
                self.validate_handoff(handoff, principal, steps=1, depth=1, tool_calls=1)
                self.store.add('agent_executions', principal.tenant_id, {'conversation_id': conversation_id,
                               'handoff': handoff.model_dump(), 'status': 'handed_off', 'timestamp': now()})
                if incoming.tool == 'CheckAvailability':
                    outcome = self.tools.execute(principal, assistant, conversation, incoming.tool, arguments,
                                                 key=incoming.event_id, correlation_id=correlation)
                    result['outcome'] = outcome
                    response = self.tools.localized(outcome, locale, tenant['timezone'], principal.tenant_id)
                else:
                    approval = self.store.add('approvals', principal.tenant_id, {
                        'conversation_id': conversation_id, 'assistant_id': assistant['id'], 'tool': incoming.tool,
                        'arguments': arguments, 'locale': locale, 'correlation_id': correlation,
                        'requested_by': principal.user_id, 'status': 'pending',
                        'expires_at': (self.clock() + timedelta(minutes=15)).isoformat(),
                        'fingerprint': sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest()})
                    result['approval'] = approval
                    response = tr(locale, 'approval_required')
            elif conversation.get('human_escalation'):
                response = tr(locale, 'escalated')
            elif any(keyword.casefold() in incoming.content.casefold() for keyword in assistant.get('escalation_rules', {}).get('keywords', []) if keyword):
                self.tools.authorize(principal, assistant, 'EscalateToHuman')
                handoff = Handoff(tenant_id=principal.tenant_id, conversation_id=conversation_id,
                                  intent='EscalateToHuman', arguments={'reason': incoming.content[:500]}, locale=locale, correlation_id=correlation)
                self.validate_handoff(handoff, principal, steps=1, depth=1, tool_calls=1)
                self.store.add('agent_executions', principal.tenant_id, {'conversation_id': conversation_id,
                               'handoff': handoff.model_dump(), 'status': 'awaiting_confirmation', 'timestamp': now()})
                approval = self.store.add('approvals', principal.tenant_id, {
                    'conversation_id': conversation_id, 'assistant_id': assistant['id'], 'tool': 'EscalateToHuman',
                    'arguments': {'reason': incoming.content[:500]}, 'locale': locale, 'correlation_id': correlation,
                    'requested_by': principal.user_id, 'status': 'pending',
                    'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
                    'fingerprint': sha256(json.dumps({'reason': incoming.content[:500]}, sort_keys=True).encode()).hexdigest()})
                result['approval'] = approval
                response = tr(locale, 'approval_required')
            elif not faq_answered:
                if assistant.get('public_knowledge_only') and 'ConciergeBooking' in assistant['allowed_tools']:
                    intent=self.booking.receptionist.interpret(incoming.content,locale,provider=provider)
                    if intent.intent in ('book','details','confirm','cancel'):
                        response=('Изберете действие за демонстрация. За записване потвърдете имейла си; за промяна или отказ използвайте личната връзка от имейла. Нищо не е променено.' if locale=='bg-BG' else 'Choose a demo action. Verify your email to book; use your private email link to reschedule or cancel. Nothing has been changed.')
                else:
                    natural = self.booking.handle(principal, assistant, conversation, incoming, locale, correlation, received_at, provider=provider,
                        reference_at=context.get('relative_date_reference_at'))
                    if natural is not None:
                        result.update(natural)
                        response = natural['response']
            if response is None:
                response = (('Мога да помогна с одобрена информация за Ontelyx. Изберете демонстрация или бизнес запитване.' if locale=='bg-BG' else 'I can help with approved Ontelyx information. Choose a demo or a business inquiry.')
                    if assistant.get('public_knowledge_only') else provider.reply(incoming.content, locale, assistant['instructions']))
            result['llm_provider'] = provider.capability.provider
            result['state'] = provider.capability.state
            result['response'] = response
            # Opt-out acknowledgements are permitted once; subsequent outbound SMS is blocked.
            if not result.pop('already_dispatched', False):
                result['delivery'] = self.dispatch(principal, assistant, conversation, response, locale, correlation, recipient=sender, opt_out_ack=stop)
            self.store.add('provider_events', principal.tenant_id, {'conversation_id': conversation_id, 'result': result,
                           'channel': conversation['channel'], 'external_id': incoming.event_id, 'timestamp': now(),
                           'fingerprint': sha256(incoming.model_dump_json().encode()).hexdigest()}, external_key=key)
            self.store.add('usage_records', principal.tenant_id, {'channel': conversation['channel'], 'messages': 1,
                           'kind': 'opt_out' if stop else 'agent_execution', 'billing_precharged': bool(self.store.entitlements),
                           'agent': 'receptionist', 'llm_input_tokens': None, 'llm_output_tokens': None,
                           'token_usage_status': 'separate_inference_receipts' if provider.capability.provider == 'qwen' else 'not_reported_by_mock',
                           'correlation_id': correlation, 'timestamp': now(), 'provider': provider.capability.provider})
            self.store.audit(principal, 'message:received', correlation_id=correlation, resource_id=conversation_id)
            return result

    @staticmethod
    def validate_handoff(handoff, principal, *, steps, depth, tool_calls):
        if handoff.tenant_id != principal.tenant_id or handoff.source_agent != 'receptionist' or handoff.target_agent != 'executor':
            raise DomainError('forbidden', 403)
        if steps > handoff.max_steps or depth > handoff.max_depth or tool_calls > handoff.tool_budget:
            raise DomainError('budget_exceeded', 409)

    def dispatch(self, principal, assistant, conversation, text, locale, correlation, *, recipient='user', opt_out_ack=False, at=None, kind='response'):
        if self.messaging and conversation.get('connection_id'):
            return self.messaging.queue_response(principal, assistant, conversation, text, locale, correlation, at=at, opt_out_ack=opt_out_ack, kind=kind)
        channel = conversation['channel']
        category = {'sms': 'sms_segments', 'email': 'email_messages', 'whatsapp': 'whatsapp_messages'}.get(channel)
        quantity = sms_segments(text)['segments'] if channel == 'sms' else 1
        if self.store.entitlements and category and not opt_out_ack:
            self.store.entitlements.check(principal.tenant_id, category, quantity)
        contact = self.store.get('contacts', principal.tenant_id, conversation['contact_id']) if conversation.get('contact_id') else {}
        if channel == 'sms' and contact.get('sms_opt_out') and not opt_out_ack:
            raise DomainError('forbidden', 403)
        if channel in ('sms', 'whatsapp') and recipient == 'user':
            recipient = contact.get('address', '+359888000001')  # Synthetic mock recipient only.
        if channel == 'email' and recipient == 'user':
            recipient = contact.get('address', 'synthetic@example.invalid')
        at = at or self.clock()
        last_inbound = conversation.get('last_inbound_at')
        window_open = bool(last_inbound and at - datetime.fromisoformat(last_inbound) <= timedelta(hours=24))
        message = Message(id=uid(), tenant_id=principal.tenant_id, assistant_id=assistant['id'], conversation_id=conversation['id'],
                          provider=self.providers.channels[channel].capability.provider,
                          channel=channel, external_id=uid(), sender='assistant', recipient=recipient, content=text, locale=locale,
                          timestamp=at, status='pending', direction='outbound', correlation_id=correlation,
                          metadata={'window_open': window_open, 'correlation_id': correlation, 'agent': 'human' if kind=='human' else 'receptionist', 'kind':kind})
        delivery = self.providers.channels[channel].send(message)
        if self.store.entitlements and category:
            self.store.entitlements.record(principal.tenant_id, UsageEvent(resource_id=message.id, category=category, quantity=quantity,
                unit=UNITS[category], provider='mock', timestamp=self.clock(), correlation_id=correlation,
                idempotency_key='outbound:' + message.id), enforce=False)
        self.store.add('messages', principal.tenant_id, {**message.model_dump(mode='json'), 'direction': 'outbound', 'delivery': delivery,
            'status': delivery['status'], 'delivery_status': delivery['status'],
            'expires_at': (self.clock() + timedelta(days=self.store.tenant(principal.tenant_id)['retention_days'])).isoformat()}, id=message.id)
        return delivery

    def approve(self, principal, approval_id):
        principal.require('approve')
        if self.store.entitlements: self.store.entitlements.access(principal.tenant_id)
        with self.store.transaction():
            approval = self.store.get('approvals', principal.tenant_id, approval_id)
            if approval['status'] == 'completed':
                return approval['result']
            if approval['status'] != 'pending' or datetime.fromisoformat(approval['expires_at']) < self.clock():
                raise DomainError('expired', 409)
            if approval['fingerprint'] != sha256(json.dumps(approval['arguments'], sort_keys=True).encode()).hexdigest():
                raise DomainError('invalid_input', 422)
            conversation = self.store.get('conversations', principal.tenant_id, approval['conversation_id'])
            assistant = self.configuration(principal, conversation)
            if assistant['status'] != 'active' or conversation['channel'] not in assistant['enabled_channels']:
                raise DomainError('disabled', 409)
            if conversation.get('human_escalation') and assistant.get('escalation_rules', {}).get('pause_automation', True) and approval['tool'] != 'EscalateToHuman':
                raise DomainError('disabled', 409)
            outcome = self.tools.execute(principal, assistant, conversation, approval['tool'], approval['arguments'],
                                         key=approval_id, correlation_id=approval['correlation_id'], approved=True)
            if conversation['channel'] == 'voice' and approval['tool'] == 'CreateAppointment' and self.store.operations:
                self.store.operations.trace_voice(principal.tenant_id, 'tool_completed', request_correlation.get(),
                    call_id=conversation.get('call_session_id'), approval_id=approval_id,
                    parent_correlation_id=approval['correlation_id'])
                trace_correlation = request_correlation.get()
                appointment_id = outcome['data']['id']
                def trace_committed_appointment():
                    # Observation callbacks also run after rollback. Verify actual
                    # committed entities before claiming persistence in the trace.
                    try:
                        saved = self.store.get('approvals', principal.tenant_id, approval_id)
                        appointment = self.store.get('appointments', principal.tenant_id, appointment_id)
                    except DomainError:
                        return
                    if saved['status'] == 'completed' and appointment['status'] == 'confirmed':
                        self.store.operations.trace_voice(principal.tenant_id, 'appointment_persisted', trace_correlation,
                            call_id=conversation.get('call_session_id'), approval_id=approval_id, appointment_id=appointment_id,
                            parent_correlation_id=approval['correlation_id'])
                self.store.after_transaction(trace_committed_appointment)
            locale = approval['locale']
            response = self.booking.receptionist.outcome_reply(outcome, locale,
                approval.get('timezone', self.store.tenant(principal.tenant_id)['timezone']), self.tools, principal.tenant_id)
            delivery = self.dispatch(principal, assistant, conversation, response, locale, approval['correlation_id'], kind='approval_result')
            result = {'outcome': outcome, 'response': response, 'locale': locale, 'delivery': delivery, 'state': 'MOCK'}
            self.store.update('approvals', principal.tenant_id, approval_id, {'status': 'completed', 'approved_by': principal.user_id, 'result': result})
            booking = conversation.get('booking_state')
            if booking and booking.get('approval_id') == approval_id:
                self.store.update('conversations', principal.tenant_id, conversation['id'],
                                  {'booking_state': {**booking, 'status': 'completed', 'locale': locale}})
            self.store.audit(principal, 'approval:confirmed', resource_id=approval_id, correlation_id=approval['correlation_id'])
            return result
