"""Unified messaging gateway, durable inbox/outbox, notifications and human control.

All agent behavior stays in the existing Orchestrator; this module owns transport reliability.
"""
from datetime import datetime, timedelta
from hashlib import sha256
import hmac
import json
import os
from urllib.parse import urlsplit
from .domain import DomainError, Incoming, Message, Principal, NormalizedInbound
from .store import uid, event_key
from .language import tr, format_date
from .messaging_adapters import MockMessagingAdapter, MetaWhatsAppAdapter, TwilioSMSAdapter, mailbox
from .message_delivery import DeliveryFailure, send_meta, send_twilio_sms, SMTPEmailProvider
from .attachment_store import AttachmentStore
from .providers import sms_segments
from .observability import timed

NOTIFICATION_KEYS = ('appointment_created', 'appointment_rescheduled', 'appointment_cancelled', 'reminder', 'follow_up', 'human_escalation')


class MessagingGateway:
    def __init__(self, store, secrets, orchestrator):
        self.store, self.secrets, self.orchestrator = store, secrets, orchestrator
        self.clock = orchestrator.clock
        self.attachments = AttachmentStore(store, secrets, self.clock)
        self.mock = {key: MockMessagingAdapter(key) for key in ('email', 'whatsapp', 'sms', 'web_chat')}
        self.meta, self.twilio, self.smtp = MetaWhatsAppAdapter(send_meta), TwilioSMSAdapter(send_twilio_sms), SMTPEmailProvider()
        orchestrator.messaging = self
        orchestrator.tools.messaging = self

    def adapter(self, connection):
        return self.meta if connection['provider'] == 'meta' else self.twilio if connection['provider'] == 'twilio' else self.mock[connection['channel']]

    def principal(self, connection, *, recovery=False):
        user = self.store.get('users', connection['tenant_id'], connection['service_user_id'])
        if not connection.get('enabled', True) or not user['enabled']: raise DomainError('forbidden', 403)
        principal = Principal(connection['tenant_id'], user['id'], user['role'], user['subject'])
        principal.require('execute')
        if self.store.entitlements: self.store.entitlements.access(connection['tenant_id'], recovery=recovery)
        # A configured admin's connector gets operator execution scope, never configuration authority.
        return Principal(connection['tenant_id'], user['id'], 'operator', user['subject'])

    def credentials(self, connection):
        keys = ('webhook_secret', 'app_secret', 'verify_token', 'access_token', 'auth_token', 'smtp_password')
        result = {}
        for name in keys:
            if name in connection.get('credential_names', []):
                result[name] = self.secrets.get(connection['tenant_id'], 'messaging:' + connection['id'] + ':' + name)
        return result

    def configure(self, principal, config, credentials):
        principal.require('configure')
        assistant = self.store.get('assistants', principal.tenant_id, config['assistant_id'])
        channel, provider = config['channel'], config['provider']
        if channel not in assistant['enabled_channels']: raise DomainError('disabled', 409)
        if provider not in {'email': ('mock', 'smtp'), 'whatsapp': ('mock', 'meta'), 'sms': ('mock', 'twilio'), 'web_chat': ('mock',)}[channel]:
            raise DomainError('invalid_input', 422)
        config['sender_id'] = self.mock[channel].address(config['sender_id'])
        if provider != 'mock':
            origin = urlsplit(config['public_origin'])
            if origin.scheme != 'https' or not origin.hostname or origin.username or origin.password or origin.path not in ('', '/') or origin.query or origin.fragment:
                raise DomainError('invalid_input', 422)
            if config['enable_live'] and os.getenv('ASSISTANT_ENABLE_LIVE_MESSAGING') != 'true': raise DomainError('unconfigured', 503)
        required = {'mock': ('webhook_secret',), 'smtp': ('webhook_secret', 'smtp_password'),
                    'meta': ('app_secret', 'verify_token', 'access_token'), 'twilio': ('auth_token',)}[provider]
        if not all(credentials.get(key) for key in required): raise DomainError('invalid_input', 422)
        if provider in ('mock', 'smtp') and len(credentials['webhook_secret']) < 32: raise DomainError('invalid_input', 422)
        if provider == 'meta' and not (config['waba_id'].isdigit() and config['phone_number_id'].isdigit() and config['api_version']):
            raise DomainError('invalid_input', 422)
        if provider == 'twilio':
            import re
            if not re.fullmatch(r'AC[0-9a-fA-F]{32}', config['account_sid']): raise DomainError('invalid_input', 422)
        with self.store.transaction():
            self.ensure_templates(principal.tenant_id)
            record = self.store.add('channel_connections', principal.tenant_id, {**config,
                'service_user_id': principal.user_id, 'credential_names': [key for key, value in credentials.items() if value],
                'enabled': True, 'state': 'MOCK' if provider == 'mock' else 'LIVE_UNVERIFIED',
                'webhook_status': 'unverified', 'last_error': None, 'capabilities': ['inbound', 'outbox', 'callbacks', 'bg-BG', 'en-US']})
            for key, value in credentials.items():
                if value: self.secrets.put(principal.tenant_id, 'messaging:' + record['id'] + ':' + key, value)
            self.store.audit(principal, 'messaging:configured', resource_id=record['id'])
            return record

    def ensure_templates(self, tenant_id):
        for locale in ('bg-BG', 'en-US'):
            for key in NOTIFICATION_KEYS:
                existing = self.store.find('notification_templates', tenant_id, locale + ':' + key)
                defaults = {'template_key': key, 'channel': 'any', 'subject': tr(locale, 'subject'),
                            'variables': ['date'] if key in ('appointment_created', 'appointment_rescheduled', 'reminder') else ['title', 'date'] if key == 'follow_up' else [], 'status': 'active'}
                if existing:
                    self.store.update('notification_templates', tenant_id, existing['id'], {k: v for k, v in defaults.items() if k not in existing})
                else:
                    self.store.add('notification_templates', tenant_id, {'key': key, 'locale': locale, 'body': tr(locale, key, date='{date}', title='{title}'), **defaults}, external_key=locale + ':' + key)

    def ingest(self, tenant_id, connection_id, raw, headers, *, webhook_path=None, message_id=None):
        connection = self.store.get('channel_connections', tenant_id, connection_id)
        self.principal(connection, recovery=True)
        if connection['channel'] not in self.mock or 'credential_names' not in connection: raise DomainError('invalid_input', 422)
        connection = {**connection, '_webhook_path': webhook_path or '/webhooks/messaging/' + tenant_id + '/' + connection_id, '_message_id': message_id}
        adapter = self.adapter(connection)
        adapter.validate_inbound_event(raw, headers, connection, self.credentials(connection))
        events = adapter.normalize_inbound_event(raw, connection, self.clock())
        result = []
        with self.store.transaction():
            for event in events:
                key = event_key(connection_id, event.external_message_id)
                stable = event.model_dump(mode='json')
                if event.content_type in ('status', 'template_status') or connection['provider'] == 'twilio': stable.pop('timestamp')
                fingerprint = sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()
                previous = self.store.find('messaging_events', tenant_id, key)
                if previous:
                    if previous['fingerprint'] != fingerprint: raise DomainError('conflict', 409)
                    result.append({'event_id': previous['id'], 'duplicate': True, 'status': previous['status']})
                    continue
                age = (self.clock() - event.timestamp).total_seconds()
                if age < -300 or age > connection['max_event_age_seconds']: raise DomainError('expired', 409)
                record = self.store.add('messaging_events', tenant_id, {'connection_id': connection_id,
                    'external_message_id': event.external_message_id, 'fingerprint': fingerprint,
                    'normalized': event.model_dump(mode='json'), 'status': 'pending', 'received_at': self.clock().isoformat(),
                    'expires_at': (self.clock() + timedelta(days=self.store.tenant(tenant_id)['retention_days'])).isoformat()}, external_key=key)
                self.store.add('jobs', tenant_id, {'kind': 'inbound_message', 'event_id': record['id'], 'connection_id': connection_id,
                    'status': 'pending', 'attempts': 0, 'due_at': self.clock().isoformat()}, external_key='inbound:' + record['id'])
                result.append({'event_id': record['id'], 'duplicate': False, 'status': 'queued'})
            self.store.update('channel_connections', tenant_id, connection_id, {'webhook_status': 'verified'})
        return {'events': result, 'state': connection['state']}

    def conversation_for(self, principal, connection, event):
        tenant = principal.tenant_id
        # Endpoint contacts are scoped to one connection; an address/name is not a cross-channel identity grant.
        endpoint_key = event_key('endpoint:' + connection['id'], event.sender_id)
        contact = self.store.find('contacts', tenant, endpoint_key)
        if not contact:
            contact = self.store.add('contacts', tenant, {'name': event.sender_id, 'address': event.sender_id,
                'endpoint_only': True, 'preferred_locale': None, 'sms_opt_out': False,
                'sms_consent': False, 'whatsapp_consent': False}, external_key=endpoint_key)
        thread = event.metadata.get('thread_id', '')
        if connection['channel'] == 'email':
            parents = [event.metadata.get('in_reply_to', '')] + list(reversed(event.metadata.get('references', [])))
            for parent in parents:
                mapped = self.store.find('email_threads', tenant, event_key(connection['id'], parent)) if parent else None
                if mapped:
                    candidate = self.store.get('conversations', tenant, mapped['conversation_id'])
                    if candidate.get('remote_sender_id') == event.sender_id and candidate['status'] not in ('closed', 'resolved'):
                        return candidate
            thread = thread or event.external_message_id
        route = event_key(connection['id'], event.sender_id + ':' + thread)
        mapping = self.store.find('channel_threads', tenant, route)
        if mapping:
            candidate = self.store.get('conversations', tenant, mapping['conversation_id'])
            if candidate['status'] not in ('closed', 'resolved'): return candidate
        conversation = self.orchestrator.conversation(principal, connection['assistant_id'], connection['channel'], contact['id'])
        conversation = self.store.update('conversations', tenant, conversation['id'], {'connection_id': connection['id'],
            'remote_sender_id': event.sender_id, 'remote_recipient_id': event.recipient_id,
            'thread_id': thread, 'status': 'active', 'assigned_agent': 'receptionist', 'assigned_user_id': None,
            'last_message_at': event.timestamp.isoformat(), 'last_message': '', 'created_at': self.clock().isoformat()})
        if mapping:
            # Conversation ref is immutable in Store.update; replace routing payload through a dedicated validated operation.
            self.store.db.execute('UPDATE channel_threads SET conversation_id=?,data=? WHERE tenant_id=? AND id=?',
                (conversation['id'], json.dumps({**mapping, 'conversation_id': conversation['id']}), tenant, mapping['id']))
        else:
            self.store.add('channel_threads', tenant, {'conversation_id': conversation['id'], 'connection_id': connection['id']}, external_key=route)
        return conversation

    def process_inbound(self, principal, job):
        with self.store.transaction():
            record = self.store.get('messaging_events', principal.tenant_id, job['event_id'])
            if record['status'] == 'completed': return record
            if record.get('redacted') or datetime.fromisoformat(record['expires_at']) <= self.clock(): raise DomainError('expired', 409)
            connection = self.store.get('channel_connections', principal.tenant_id, record['connection_id'])
            actor = self.principal(connection, recovery=True)
            event = NormalizedInbound.model_validate(record['normalized'])
            if event.content_type == 'status':
                self.delivery_status(actor, connection, event.metadata)
                conversation = None
            elif event.content_type == 'template_status':
                language = {'bg': 'bg-BG', 'en_US': 'en-US'}.get(event.metadata['language'])
                template = next((x for x in self.store.list('approved_templates', principal.tenant_id)
                    if x['connection_id'] == connection['id'] and x['provider_name'] == event.metadata['name'] and x['locale'] == language), None)
                if template:
                    status = 'approved' if event.metadata['status'] == 'APPROVED' else 'rejected'
                    self.store.update('approved_templates', principal.tenant_id, template['id'], {'status': status, 'verified_by': 'signed_provider_callback'})
                conversation = None
            else:
                conversation = self.conversation_for(actor, connection, event)
                attachments = [self.attachments.put(principal.tenant_id, conversation['id'], item) for item in event.attachments]
                updates = {'last_customer_at': event.timestamp.isoformat(), 'last_message_at': event.timestamp.isoformat(),
                           'last_message': event.content[:240], 'email_subject': event.metadata.get('subject', conversation.get('email_subject', ''))}
                if connection['channel'] == 'email': updates['last_email_message_id'] = event.external_message_id
                conversation = self.store.update('conversations', principal.tenant_id, conversation['id'], updates)
                if connection['channel'] == 'email':
                    key = event_key(connection['id'], event.external_message_id)
                    if not self.store.find('email_threads', principal.tenant_id, key):
                        self.store.add('email_threads', principal.tenant_id, {'conversation_id': conversation['id']}, external_key=key)
                language_command = {'switch to english': 'en-US', 'премини на английски': 'en-US',
                                    'switch to bulgarian': 'bg-BG', 'премини на български': 'bg-BG'}
                locale = event.explicit_locale or language_command.get(event.content.casefold().strip(' .!'))
                result = self.orchestrator.inbound(actor, conversation['id'], Incoming(content=event.content or tr(conversation.get('active_locale') or 'en-US', 'attachment_received'),
                    event_id='messaging:' + record['id'], locale=locale), sender=event.sender_id, recipient=event.recipient_id,
                    attachments=attachments, message_context={'provider': connection['provider'], 'external_id': event.external_message_id,
                        'timestamp': event.timestamp, 'metadata': {'connection_id': connection['id'], **event.metadata}})
                current = self.store.get('conversations', principal.tenant_id, conversation['id'])
                state = 'escalated' if current['human_escalation'] else 'awaiting_approval' if result.get('approval') else 'awaiting_customer'
                self.store.update('conversations', principal.tenant_id, conversation['id'], {'status': state})
            safe = {'external_message_id': event.external_message_id, 'sender_id': event.sender_id,
                    'recipient_id': event.recipient_id, 'content_type': event.content_type, 'timestamp': event.timestamp.isoformat()}
            result = self.store.update('messaging_events', principal.tenant_id, record['id'], {'status': 'completed', 'normalized': safe,
                'resolved_conversation_id': conversation['id'] if conversation else None})
            self.meter(principal.tenant_id, connection['channel'], 'inbound_message' if conversation else 'provider_callback')
            self.store.update('jobs', principal.tenant_id, job['id'], {'status': 'completed'})
            return result

    def queue_response(self, principal, assistant, conversation, text, locale, correlation, *, kind='response',
                       metadata=None, at=None, force_approved=False, opt_out_ack=False):
        principal.require('execute')
        connection = self.store.get('channel_connections', principal.tenant_id, conversation['connection_id'])
        self.principal(connection, recovery=opt_out_ack)
        if connection['assistant_id'] != assistant['id'] or connection['channel'] != conversation['channel']:
            raise DomainError('forbidden', 403)
        key = event_key('outbound:' + conversation['id'], kind + ':' + correlation)
        fingerprint = sha256(json.dumps([text, locale, metadata or {}, opt_out_ack], sort_keys=True).encode()).hexdigest()
        previous = self.store.find('messages', principal.tenant_id, key)
        if previous:
            if previous.get('request_fingerprint') != fingerprint: raise DomainError('conflict', 409)
            return previous['delivery']
        self.ensure_templates(principal.tenant_id)
        subject = tr(locale, 'subject')
        if kind == 'response' and conversation.get('email_subject'): subject = 'Re: ' + conversation['email_subject'][:180]
        content = text + ('\n\n' + tr(locale, 'signature') if connection['channel'] == 'email' else '')
        if len(content) > 10000: raise DomainError('invalid_input', 422)
        draft = connection['channel'] == 'email' and connection['email_draft_required'] and not force_approved
        message = Message(id=uid(), tenant_id=principal.tenant_id, assistant_id=assistant['id'], conversation_id=conversation['id'],
            channel=connection['channel'], provider=connection['provider'], external_id=uid(), sender=connection['sender_id'],
            recipient=conversation['remote_sender_id'], content=content, locale=locale, timestamp=at or self.clock(),
            direction='outbound', status='draft' if draft else 'queued', correlation_id=correlation,
            type='email' if connection['channel'] == 'email' else 'text', metadata={'connection_id': connection['id'],
                'subject': subject, 'in_reply_to': conversation.get('last_email_message_id'), 'kind': kind,
                'opt_out_ack': opt_out_ack, **(metadata or {})})
        delivery = {'message_id': message.id, 'status': message.status, 'state': connection['state']}
        self.store.add('messages', principal.tenant_id, {**message.model_dump(mode='json'), 'delivery': delivery,
            'request_fingerprint': fingerprint,
            'expires_at': (self.clock() + timedelta(days=self.store.tenant(principal.tenant_id)['retention_days'])).isoformat()}, id=message.id, external_key=key)
        self.store.add('jobs', principal.tenant_id, {'kind': 'outbound_message', 'conversation_id': conversation['id'],
            'correlation_id': correlation,
            'message_id': message.id, 'connection_id': connection['id'], 'status': 'draft' if draft else 'pending',
            'attempts': 0, 'due_at': self.clock().isoformat(), **(metadata or {})}, external_key='outbound:' + message.id)
        return delivery

    def policy(self, connection, message, conversation):
        if self.store.entitlements:
            if not message['metadata'].get('opt_out_ack'): self.store.entitlements.access(connection['tenant_id'])
            category = {'sms': 'sms_segments', 'email': 'email_messages', 'whatsapp': 'whatsapp_messages'}.get(connection['channel'])
            if category and not message['metadata'].get('opt_out_ack'): self.store.entitlements.check(connection['tenant_id'], category, sms_segments(message['content'])['segments'] if category == 'sms_segments' else 1)
        if message.get('redacted') or message.get('expires_at') and datetime.fromisoformat(message['expires_at']) <= self.clock():
            raise DomainError('expired', 409)
        if conversation['status'] == 'closed': raise DomainError('disabled', 409)
        assistant = self.store.get('assistants', connection['tenant_id'], connection['assistant_id'])
        if assistant['status'] != 'active' or connection['channel'] not in assistant['enabled_channels']: raise DomainError('disabled', 409)
        contact = self.store.get('contacts', connection['tenant_id'], conversation['contact_id']) if conversation.get('contact_id') else {}
        channel = connection['channel']
        if channel == 'sms' and contact.get('sms_opt_out') and not message['metadata'].get('opt_out_ack'):
            raise DomainError('forbidden', 403)
        notification = message['metadata'].get('kind') in NOTIFICATION_KEYS
        if channel == 'sms' and notification and not contact.get('sms_consent'):
            raise DomainError('consent_required', 403)
        if channel == 'whatsapp':
            if notification and not contact.get('whatsapp_consent'):
                raise DomainError('consent_required', 403)
            last = conversation.get('last_customer_at')
            open_window = last and 0 <= (self.clock() - datetime.fromisoformat(last)).total_seconds() < 86400
            if not open_window:
                template_key = message['metadata'].get('template_key')
                template = self.store.find('approved_templates', connection['tenant_id'], event_key(connection['id'], str(template_key) + ':' + message['locale']))
                if not template or template['status'] != 'approved' or not contact.get('whatsapp_consent'):
                    raise DomainError('template_required', 403)
                message['metadata']['provider_template'] = {'name': template['provider_name'],
                    'language': {'bg-BG': 'bg', 'en-US': 'en_US'}[message['locale']],
                    'parameters': message['metadata'].get('template_parameters', [])}

    @timed('channel_delivery')
    def deliver(self, principal, job):
        with self.store.transaction():
            current = self.store.get('jobs', principal.tenant_id, job['id'])
            if current['status'] not in ('pending', 'retry'): return current
            message = self.store.get('messages', principal.tenant_id, current['message_id'])
            connection = self.store.get('channel_connections', principal.tenant_id, current['connection_id'])
            self.principal(connection, recovery=message['metadata'].get('opt_out_ack', False))
            conversation = self.store.get('conversations', principal.tenant_id, message['conversation_id'])
            self.policy(connection, message, conversation)
            if message['metadata'].get('appointment_id'):
                appointment = self.store.get('appointments', principal.tenant_id, message['metadata']['appointment_id'])
                if appointment['status'] == 'cancelled' or appointment['starts_at'] != message['metadata'].get('appointment_version'):
                    self.store.update('jobs', principal.tenant_id, current['id'], {'status': 'cancelled'})
                    self.store.update('messages', principal.tenant_id, message['id'], {'status': 'cancelled', 'delivery_status': 'cancelled'})
                    return {'status': 'cancelled'}
            recent = [x for x in self.store.list('delivery_attempts', principal.tenant_id) if x['connection_id'] == connection['id'] and
                      (self.clock() - datetime.fromisoformat(x['timestamp'])).total_seconds() < 60]
            if len(recent) >= connection['rate_per_minute']: raise DeliveryFailure('rate_limited', retry_safe=True)
            category = {'sms': 'sms_segments', 'email': 'email_messages', 'whatsapp': 'whatsapp_messages'}.get(connection['channel'])
            if self.store.entitlements and category and not message['metadata'].get('opt_out_ack'):
                self.store.entitlements.reserve(principal.tenant_id, category, sms_segments(message['content'])['segments'] if category == 'sms_segments' else 1, message['id'])
            attempt = self.store.add('delivery_attempts', principal.tenant_id, {'conversation_id': message['conversation_id'],
                'connection_id': connection['id'], 'message_id': message['id'], 'timestamp': self.clock().isoformat(), 'status': 'sending'})
            self.store.update('jobs', principal.tenant_id, current['id'], {'status': 'sending', 'attempts': current['attempts'] + 1,
                             'lease_until': (self.clock() + timedelta(seconds=30)).isoformat()})
        # Network I/O deliberately happens after the database claim commits.
        try:
            provider = self.smtp if connection['provider'] == 'smtp' else self.adapter(connection)
            result = provider.send_message(message, connection, self.credentials(connection), message['id'])
        except Exception as error:
            if not isinstance(error, DomainError): error = DeliveryFailure(uncertain=True)
            with self.store.transaction():
                latest = self.store.get('jobs', principal.tenant_id, current['id'])
                uncertain = isinstance(error, DeliveryFailure) and error.uncertain
                retry = isinstance(error, DeliveryFailure) and error.retry_safe and latest['attempts'] < 4
                state = 'uncertain' if uncertain else 'retry' if retry else 'dead_letter'
                if self.store.entitlements: self.store.entitlements.release(principal.tenant_id, message['id'], 'uncertain' if uncertain else 'released')
                self.store.update('jobs', principal.tenant_id, current['id'], {'status': state, 'error_code': error.code,
                    'due_at': (self.clock() + timedelta(seconds=2 ** latest['attempts'] * 5)).isoformat()})
                self.store.update('messages', principal.tenant_id, message['id'], {'status': state, 'delivery_status': state})
                self.store.update('delivery_attempts', principal.tenant_id, attempt['id'], {'status': state, 'error_code': error.code})
                self.store.update('channel_connections', principal.tenant_id, connection['id'], {'last_error': error.code})
                self.meter(principal.tenant_id, connection['channel'], 'provider_error', message_id=message['id'])
                if self.store.operations: self.store.operations.observe('provider_error', principal.tenant_id, error=error.code)
            return {'status': state, 'code': error.code}
        with self.store.transaction():
            latest_message = self.store.get('messages', principal.tenant_id, message['id'])
            status = latest_message['delivery_status'] if latest_message['delivery_status'] in ('delivered', 'read') else result['status']
            delivery = {**result, 'status': status, 'message_id': message['id']}
            self.store.update('messages', principal.tenant_id, message['id'], {'status': status, 'delivery_status': status,
                'external_id': result['external_message_id'], 'external_message_id': result['external_message_id'], 'delivery': delivery})
            self.store.update('jobs', principal.tenant_id, current['id'], {'status': 'completed'})
            self.store.update('delivery_attempts', principal.tenant_id, attempt['id'], {'status': 'accepted'})
            if connection['channel'] == 'email':
                key = event_key(connection['id'], result['external_message_id'])
                if not self.store.find('email_threads', principal.tenant_id, key):
                    self.store.add('email_threads', principal.tenant_id, {'conversation_id': message['conversation_id']}, external_key=key)
            segments = sms_segments(message['content'])['segments'] if connection['channel'] == 'sms' else 0
            self.meter(principal.tenant_id, connection['channel'], 'outbound_message', message_id=message['id'], segments=segments, provider=connection['provider'])
            if self.store.entitlements: self.store.entitlements.release(principal.tenant_id, message['id'], 'settled')
            if message['metadata'].get('kind') in NOTIFICATION_KEYS:
                self.meter(principal.tenant_id, connection['channel'], 'notification_delivery', message_id=message['id'], template_key=message['metadata']['kind'])
            self.store.audit(principal, 'message:dispatched', resource_id=message['id'])
            return delivery

    def meter(self, tenant, channel, kind, **values):
        key = 'outbound:' + values['message_id'] if kind == 'outbound_message' and values.get('message_id') else None
        if key:
            previous = self.store.find('usage_records', tenant, key)
            if previous: return previous
            reservation = self.store.find('usage_reservations', tenant, key)
            if reservation: values.update(occurred_at=reservation['timestamp'], plan_snapshot=reservation['plan_snapshot'])
        return self.store.add('usage_records', tenant, {'channel': channel, 'kind': kind, 'timestamp': self.clock().isoformat(), 'price': None, **values}, external_key=key)

    def delivery_status(self, principal, connection, payload):
        status = payload['status']
        if status not in ('sent', 'delivered', 'read', 'failed'): raise DomainError('invalid_input', 422)
        if payload.get('message_id'):
            message = self.store.get('messages', principal.tenant_id, payload['message_id'])
        else:
            matches = [x for x in self.store.list('messages', principal.tenant_id) if x.get('direction') == 'outbound'
                and x.get('external_message_id') == payload['provider_message_id'] and x.get('metadata', {}).get('connection_id') == connection['id']]
            if len(matches) != 1: raise DomainError('not_found', 404)
            message = matches[0]
        if message['metadata'].get('connection_id') != connection['id'] or message['direction'] != 'outbound': raise DomainError('forbidden', 403)
        existing = message.get('external_message_id')
        if existing != payload['provider_message_id'] and message['delivery_status'] not in ('queued', 'draft', 'uncertain'):
            raise DomainError('forbidden', 403)
        ranks = {'queued': 0, 'draft': 0, 'simulated': 0, 'sent': 1, 'delivered': 2, 'read': 3, 'failed': 4, 'uncertain': 0}
        current = message['delivery_status']
        if current in ('read', 'failed') or current == 'delivered' and status == 'failed' or ranks.get(status, 0) < ranks.get(current, 0): return {'status': current, 'ignored': True}
        if status in ('sent', 'delivered', 'read'):
            self.meter(principal.tenant_id, connection['channel'], 'outbound_message', message_id=message['id'],
                segments=sms_segments(message['content'])['segments'] if connection['channel'] == 'sms' else 0, provider=connection['provider'])
            if self.store.entitlements: self.store.entitlements.release(principal.tenant_id, message['id'], 'settled')
        return self.store.update('messages', principal.tenant_id, message['id'], {'status': status, 'delivery_status': status,
            'external_id': payload['provider_message_id'], 'external_message_id': payload['provider_message_id'],
            'delivery': {**message.get('delivery', {}), 'status': status, 'error_code': payload.get('error_code')}})

    def run(self, principal, *, limit=20):
        principal.require('approve')
        result = []
        for job in self.store.list('jobs', principal.tenant_id):
            if len(result) >= limit: break
            if job['kind'] not in ('inbound_message', 'outbound_message', 'scheduled_notification'): continue
            if job['status'] == 'sending' and datetime.fromisoformat(job['lease_until']) <= self.clock():
                self.store.update('jobs', principal.tenant_id, job['id'], {'status': 'uncertain', 'error_code': 'delivery_unknown'})
                self.store.update('messages', principal.tenant_id, job['message_id'], {'status': 'uncertain', 'delivery_status': 'uncertain'})
                continue  # Crash/lease expiration may mean the provider accepted the send. Never blindly retry.
            if job['status'] not in ('pending', 'retry') or datetime.fromisoformat(job['due_at']) > self.clock(): continue
            try:
                item = self.process_inbound(principal, job) if job['kind'] == 'inbound_message' else self.prepare_notification(principal, job) if job['kind'] == 'scheduled_notification' else self.deliver(principal, job)
                result.append({'job_id': job['id'], 'status': item.get('status', 'completed')})
            except DomainError as error:
                if self.store.operations: self.store.operations.observe('background_job', principal.tenant_id, error=error.code)
                retry = isinstance(error, DeliveryFailure) and error.retry_safe and job['attempts'] < 4
                state = 'retry' if retry else 'dead_letter'
                self.store.update('jobs', principal.tenant_id, job['id'], {'status': state, 'error_code': error.code,
                    'attempts': job['attempts'] + 1, 'due_at': (self.clock() + timedelta(seconds=30)).isoformat()})
                if job.get('message_id'):
                    self.store.update('messages', principal.tenant_id, job['message_id'], {'status': state, 'delivery_status': state})
                result.append({'job_id': job['id'], 'status': state, 'code': error.code})
            except Exception:
                # Malformed signed connector data must not stop the bounded worker.
                # Inbound execution is transactional; unknown delivery errors are handled in deliver().
                self.store.update('jobs', principal.tenant_id, job['id'], {'status': 'dead_letter', 'error_code': 'provider_error'})
                result.append({'job_id': job['id'], 'status': 'dead_letter', 'code': 'provider_error'})
        return result

    def schedule_notification(self, principal, conversation_id, template_key, variables, due_at, request_id):
        principal.require('approve')
        conversation = self.store.get('conversations', principal.tenant_id, conversation_id)
        if template_key not in NOTIFICATION_KEYS or conversation['status'] == 'closed' or not conversation.get('connection_id'):
            raise DomainError('invalid_input', 422)
        if due_at.tzinfo is None or due_at < self.clock(): raise DomainError('invalid_input', 422)
        self.ensure_templates(principal.tenant_id)
        template = self.store.find('notification_templates', principal.tenant_id, (conversation['active_locale'] or 'en-US') + ':' + template_key)
        if set(variables) != set(template['variables']) or any(not isinstance(v, str) or len(v) > 500 for v in variables.values()):
            raise DomainError('invalid_input', 422)
        key = event_key('notification:' + conversation_id, request_id)
        previous = self.store.find('jobs', principal.tenant_id, key)
        fingerprint = sha256(json.dumps([template_key, variables, due_at.isoformat()], sort_keys=True).encode()).hexdigest()
        if previous:
            if previous['fingerprint'] != fingerprint: raise DomainError('conflict', 409)
            return previous
        result = self.store.add('jobs', principal.tenant_id, {'conversation_id': conversation_id, 'kind': 'scheduled_notification',
            'connection_id': conversation['connection_id'], 'template_key': template_key, 'variables': variables,
            'fingerprint': fingerprint, 'due_at': due_at.isoformat(), 'attempts': 0, 'status': 'pending'}, external_key=key)
        self.store.audit(principal, 'notification:scheduled', resource_id=result['id'])
        return result

    def prepare_notification(self, principal, job):
        with self.store.transaction():
            conversation = self.store.get('conversations', principal.tenant_id, job['conversation_id'])
            if conversation['status'] == 'closed': raise DomainError('disabled', 409)
            assistant = self.store.get('assistants', principal.tenant_id, conversation['assistant_id'])
            contact = self.store.get('contacts', principal.tenant_id, conversation['contact_id']) if conversation.get('contact_id') else {}
            locale = self.orchestrator.languages.resolve('', contact=contact.get('preferred_locale'), conversation=conversation['active_locale'],
                assistant=assistant['default_locale'], tenant=self.store.tenant(principal.tenant_id)['default_locale']).locale
            template = self.store.find('notification_templates', principal.tenant_id, locale + ':' + job['template_key'])
            if template['status'] != 'active': raise DomainError('disabled', 409)
            self.queue_response(principal, assistant, conversation, template['body'].format(**job['variables']), locale, job['id'],
                kind=job['template_key'], metadata={'template_key': job['template_key'], 'template_parameters': [job['variables'][k] for k in template['variables']]})
            return self.store.update('jobs', principal.tenant_id, job['id'], {'status': 'completed'})

    def worker_tick(self):
        """One-process worker: use current service membership, never a global tenant grant."""
        with self.store.lock:
            tenants = self.store.db.execute('SELECT id FROM tenants').fetchall()
        for tenant in tenants:
            connections = [c for c in self.store.list('channel_connections', tenant['id']) if 'credential_names' in c]
            for connection in connections:
                try:
                    principal = self.principal(connection, recovery=True)
                    from .jobs import ReminderQueue
                    ReminderQueue(self.store, self.orchestrator).run_due(principal, at=self.clock())
                    self.run(principal)
                    break
                except DomainError:
                    continue

    def approve_draft(self, principal, message_id):
        principal.require('approve')
        with self.store.transaction():
            message = self.store.get('messages', principal.tenant_id, message_id)
            if message['delivery_status'] != 'draft': return message
            self.store.update('messages', principal.tenant_id, message_id, {'status': 'queued', 'delivery_status': 'queued', 'approved_by': principal.user_id})
            job = self.store.find('jobs', principal.tenant_id, 'outbound:' + message_id)
            self.store.update('jobs', principal.tenant_id, job['id'], {'status': 'pending'})
            self.store.audit(principal, 'draft:approved', resource_id=message_id)
            return self.store.get('messages', principal.tenant_id, message_id)

    def human_control(self, principal, conversation_id, action):
        principal.require('approve')
        conversation = self.store.get('conversations', principal.tenant_id, conversation_id)
        changes = {'takeover': {'status': 'escalated', 'human_escalation': True, 'assigned_agent': 'human', 'assigned_user_id': principal.user_id},
                   'resume': {'status': 'active', 'human_escalation': False, 'assigned_agent': 'receptionist', 'assigned_user_id': None},
                   'close': {'status': 'closed', 'human_escalation': True}}
        if action not in changes: raise DomainError('invalid_input', 422)
        if conversation['status'] == 'closed' and action != 'close': raise DomainError('invalid_transition', 409)
        result = self.store.update('conversations', principal.tenant_id, conversation_id, changes[action])
        if action in ('close', 'takeover'):
            for job in self.store.list('jobs', principal.tenant_id, conversation_id):
                if job['status'] in ('pending', 'retry', 'draft') and (action == 'close' or job.get('kind') == 'outbound_message' and
                        self.store.get('messages', principal.tenant_id, job['message_id'])['metadata'].get('kind') == 'response'):
                    self.store.update('jobs', principal.tenant_id, job['id'], {'status': 'cancelled'})
                    if job.get('message_id'): self.store.update('messages', principal.tenant_id, job['message_id'], {'status': 'cancelled', 'delivery_status': 'cancelled'})
        self.store.audit(principal, 'conversation:' + action, resource_id=conversation_id)
        return result

    def human_reply(self, principal, conversation_id, content, key):
        principal.require('approve')
        with self.store.transaction():
            conversation = self.store.get('conversations', principal.tenant_id, conversation_id)
            if not conversation['human_escalation'] or conversation['status'] == 'closed': raise DomainError('forbidden', 403)
            assistant = self.store.get('assistants', principal.tenant_id, conversation['assistant_id'])
            if conversation.get('connection_id'):
                result = self.queue_response(principal, assistant, conversation, content, conversation['active_locale'] or assistant['default_locale'],
                                            'human:' + key, kind='human', force_approved=True)
            else:
                previous = self.store.find('provider_events', principal.tenant_id, 'human:' + conversation_id + ':' + key)
                if previous: return previous['result']
                result = self.orchestrator.dispatch(principal, assistant, conversation, content,
                      conversation['active_locale'] or assistant['default_locale'], 'human:' + key, kind='human')
                self.store.add('provider_events', principal.tenant_id, {'result': result}, external_key='human:' + conversation_id + ':' + key)
            self.store.audit(principal, 'human:replied', resource_id=conversation_id)
            return result

    def cancel_obsolete(self, tenant, appointment_id, version=None):
        for job in self.store.list('jobs', tenant):
            if job.get('appointment_id') == appointment_id and job['kind'] == 'outbound_message' and job['status'] in ('pending', 'retry', 'draft'):
                if version is None or job.get('appointment_version') != version:
                    self.store.update('jobs', tenant, job['id'], {'status': 'cancelled'})
                    self.store.update('messages', tenant, job['message_id'], {'status': 'cancelled', 'delivery_status': 'cancelled'})

    def reminder(self, principal, job, appointment, conversation):
        self.ensure_templates(principal.tenant_id)
        contact = self.store.get('contacts', principal.tenant_id, conversation['contact_id']) if conversation.get('contact_id') else {}
        locale = self.orchestrator.languages.resolve('', contact=contact.get('preferred_locale'), conversation=conversation.get('active_locale'),
                                                     assistant=appointment['locale'], tenant=self.store.tenant(principal.tenant_id)['default_locale']).locale
        template = self.store.find('notification_templates', principal.tenant_id, locale + ':reminder')
        if template['status'] != 'active': raise DomainError('disabled', 409)
        date = format_date(appointment['starts_at'], locale, self.store.tenant(principal.tenant_id)['timezone'])
        body = template['body'].format(date=date)
        assistant = self.store.get('assistants', principal.tenant_id, conversation['assistant_id'])
        return self.queue_response(principal, assistant, conversation, body, locale, job['id'] + ':' + appointment['starts_at'], kind='reminder',
            metadata={'template_key': 'reminder', 'template_parameters': [date], 'appointment_id': appointment['id'],
                      'appointment_version': appointment['starts_at']})

    def delete_content(self, principal, conversation_id):
        principal.require('configure')
        with self.store.transaction():
            conversation = self.store.get('conversations', principal.tenant_id, conversation_id)
            if any(c['status'] not in ('ended', 'failed', 'transferred') for c in self.store.list('call_sessions', principal.tenant_id, conversation_id)):
                raise DomainError('conflict', 409)
            self.human_control(principal, conversation_id, 'close')
            for message in self.store.list('messages', principal.tenant_id, conversation_id):
                self.store.update('messages', principal.tenant_id, message['id'], {'content': '', 'attachments': [], 'metadata': {}, 'redacted': True})
            for attachment in self.store.list('attachments', principal.tenant_id, conversation_id):
                secret = self.store.find('secrets', principal.tenant_id, 'attachment:' + attachment['id'])
                if secret: self.store.update('secrets', principal.tenant_id, secret['id'], {'encrypted': ''})
                self.store.update('attachments', principal.tenant_id, attachment['id'], {'redacted': True})
            for job in self.store.list('jobs', principal.tenant_id, conversation_id):
                if job['status'] not in ('completed', 'cancelled'): self.store.update('jobs', principal.tenant_id, job['id'], {'status': 'cancelled'})
            for event in self.store.list('provider_events', principal.tenant_id, conversation_id):
                self.store.update('provider_events', principal.tenant_id, event['id'], {'result': {'redacted': True}})
            for event in self.store.list('messaging_events', principal.tenant_id):
                normalized = event.get('normalized', {})
                pending_endpoint = event['status'] == 'pending' and event['connection_id'] == conversation.get('connection_id') and normalized.get('sender_id') == conversation.get('remote_sender_id')
                if event.get('resolved_conversation_id') == conversation_id or pending_endpoint:
                    self.store.update('messaging_events', principal.tenant_id, event['id'], {'normalized': {}, 'redacted': True})
                    inbound = self.store.find('jobs', principal.tenant_id, 'inbound:' + event['id'])
                    if inbound and inbound['status'] != 'completed': self.store.update('jobs', principal.tenant_id, inbound['id'], {'status': 'cancelled'})
            self.store.update('conversations', principal.tenant_id, conversation_id, {'last_message': '', 'booking_state': None,
                'email_subject': '', 'content_redacted': True})
            record = self.store.add('deletion_requests', principal.tenant_id, {'conversation_id': conversation_id,
                'status': 'content_redacted', 'retained_scope': ['appointments', 'tool_audit', 'contact_identity'], 'timestamp': self.clock().isoformat()})
            self.store.audit(principal, 'content:redacted', resource_id=conversation_id)
            return record

    def purge_expired(self, principal):
        principal.require('configure')
        count = 0
        with self.store.transaction():
            for message in self.store.list('messages', principal.tenant_id):
                if not message.get('redacted') and message.get('expires_at') and datetime.fromisoformat(message['expires_at']) <= self.clock():
                    self.store.update('messages', principal.tenant_id, message['id'], {'content': '', 'attachments': [], 'metadata': {}, 'redacted': True})
                    outbox = self.store.find('jobs', principal.tenant_id, 'outbound:' + message['id'])
                    if outbox and outbox['status'] in ('pending', 'retry', 'draft'):
                        self.store.update('jobs', principal.tenant_id, outbox['id'], {'status': 'cancelled'})
                    for event in self.store.list('provider_events', principal.tenant_id, message['conversation_id']):
                        if event.get('result', {}).get('correlation_id') == message['correlation_id']:
                            self.store.update('provider_events', principal.tenant_id, event['id'], {'result': {'redacted': True}})
                    count += 1
            for item in self.store.list('attachments', principal.tenant_id):
                if not item.get('redacted') and datetime.fromisoformat(item['expires_at']) <= self.clock():
                    secret = self.store.find('secrets', principal.tenant_id, 'attachment:' + item['id'])
                    if secret: self.store.update('secrets', principal.tenant_id, secret['id'], {'encrypted': ''})
                    self.store.update('attachments', principal.tenant_id, item['id'], {'redacted': True})
                    count += 1
            for event in self.store.list('messaging_events', principal.tenant_id):
                if not event.get('redacted') and datetime.fromisoformat(event['expires_at']) <= self.clock():
                    self.store.update('messaging_events', principal.tenant_id, event['id'], {'normalized': {}, 'redacted': True})
                    inbound = self.store.find('jobs', principal.tenant_id, 'inbound:' + event['id'])
                    if inbound and inbound['status'] in ('pending', 'retry'):
                        self.store.update('jobs', principal.tenant_id, inbound['id'], {'status': 'cancelled'})
                    count += 1
            for conversation in self.store.list('conversations', principal.tenant_id):
                history = self.store.list('messages', principal.tenant_id, conversation['id'])
                if history and all(m.get('redacted') for m in history):
                    self.store.update('conversations', principal.tenant_id, conversation['id'], {'last_message': '', 'booking_state': None, 'email_subject': ''})
            self.store.audit(principal, 'messaging:retention_redacted')
        return {'redacted': count, 'retained_scope': ['business_records', 'audit', 'contact_identity']}
