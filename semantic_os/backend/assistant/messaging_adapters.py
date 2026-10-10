"""Provider normalization boundaries. Untrusted channel text never becomes tool authority."""
import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import re
from urllib.parse import parse_qsl
from email.utils import parseaddr
from .domain import Capability, DomainError, NormalizedInbound
from .email import parse_mime
from .providers import e164, sms_segments, safe_email_html


def mailbox(value):
    if any(c in value for c in '\r\n\0'): raise DomainError('invalid_input', 422)
    address = parseaddr(value)[1]
    if not re.fullmatch(r'[^\s@<>]{1,64}@[^\s@<>]{1,180}\.[^\s@<>]{2,}', address):
        raise DomainError('invalid_input', 422)
    local, domain = address.rsplit('@', 1)
    return local + '@' + domain.lower()


class MockMessagingAdapter:
    def __init__(self, channel):
        self.channel = channel
        self.capability = Capability('mock', 'MOCK', features=('normalization', 'delivery', 'idempotency', 'both_locales'))
        self.sent = {}  # Test-only provider idempotency; application ledger is persistent.
        self.failures = []

    def validate_inbound_event(self, body, headers, connection, credentials):
        secret = credentials.get('webhook_secret', '')
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not secret or not hmac.compare_digest(expected, headers.get('x-signature', '')):
            raise DomainError('invalid_signature', 401)

    def resolve_channel_connection(self, connection, recipient_id):
        if self.address(recipient_id) != self.address(connection['sender_id']):
            raise DomainError('forbidden', 403)

    def address(self, value):
        return mailbox(value) if self.channel == 'email' else e164(value) if self.channel in ('sms', 'whatsapp') else value

    def normalize_inbound_event(self, body, connection, received_at):
        try:
            payload = json.loads(body)
            if payload.get('kind') == 'status':
                return [NormalizedInbound(external_message_id=payload['event_id'], sender_id=connection['sender_id'],
                    recipient_id=connection['sender_id'], timestamp=received_at, content_type='status',
                    metadata=self.process_delivery_status(payload))]
            if self.channel == 'email' and 'mime_base64' in payload:
                raw = base64.b64decode(payload['mime_base64'], validate=True)
                parsed = parse_mime(raw)
                payload.update(external_message_id=parsed['message_id'], sender_id=parsed['sender'],
                    recipient_id=payload.get('recipient_id', parsed['recipient']), content=parsed['body'], attachments=parsed['attachments'],
                    metadata={**payload.get('metadata', {}), 'subject': parsed['subject'], 'in_reply_to': parsed['in_reply_to'],
                              'references': parsed.get('references', []), 'sender_verified': payload.get('sender_verified', False)})
            event = NormalizedInbound.model_validate({key: value for key, value in payload.items()
                if key in NormalizedInbound.model_fields})
            event.sender_id, event.recipient_id = self.address(event.sender_id), self.address(event.recipient_id)
            self.resolve_channel_connection(connection, event.recipient_id)
            if self.channel == 'email' and connection.get('require_sender_validation', True) and event.metadata.get('sender_verified') is not True:
                raise DomainError('forbidden', 403)
            return [event]
        except (ValueError, KeyError, TypeError, AttributeError):
            raise DomainError('invalid_input', 422) from None

    def send_message(self, message, connection, credentials, idempotency_key):
        if idempotency_key in self.sent: return self.sent[idempotency_key]
        if self.failures:
            raise self.failures.pop(0)
        result = {'external_message_id': 'mock:' + message['id'], 'status': 'simulated', 'state': 'MOCK'}
        if self.channel == 'sms': result.update(sms_segments(message['content']))
        if self.channel == 'email': result['safe_html'] = safe_email_html(message['content'])
        self.sent[idempotency_key] = result
        return result

    def process_delivery_status(self, payload):
        if payload.get('status') not in ('sent', 'delivered', 'read', 'failed'):
            raise DomainError('invalid_input', 422)
        return {'provider_message_id': payload['provider_message_id'], 'status': payload['status'],
                'message_id': payload.get('message_id'), 'error_code': payload.get('error_code')}

    def handle_provider_error(self, code):
        return {'code': code, 'retry_safe': False}


class MetaWhatsAppAdapter(MockMessagingAdapter):
    """Official Cloud API shapes/signatures; live HTTP is separately gated."""
    def __init__(self, sender=None):
        super().__init__('whatsapp')
        self.sender = sender
        self.capability = Capability('meta', 'LIVE_UNVERIFIED', features=('cloud_api', 'templates', 'delivery_callbacks'))

    def validate_inbound_event(self, body, headers, connection, credentials):
        expected = 'sha256=' + hmac.new(credentials.get('app_secret', '').encode(), body, hashlib.sha256).hexdigest()
        if not credentials.get('app_secret') or not hmac.compare_digest(expected, headers.get('x-hub-signature-256', '')):
            raise DomainError('invalid_signature', 401)

    def normalize_inbound_event(self, body, connection, received_at):
        try:
            payload = json.loads(body)
            if payload.get('object') != 'whatsapp_business_account': raise DomainError('invalid_input', 422)
            events = []
            for entry in payload.get('entry', []):
                if entry['id'] != connection['waba_id']: raise DomainError('forbidden', 403)
                for change in entry.get('changes', []):
                    value = change['value']
                    if change['field'] == 'message_template_status_update':
                        events.append(NormalizedInbound(external_message_id='template:' + str(value['message_template_id']) + ':' + value['event'],
                            sender_id=connection['sender_id'], recipient_id=connection['sender_id'], timestamp=received_at,
                            content_type='template_status', metadata={'name': value['message_template_name'],
                            'language': value['message_template_language'], 'status': value['event']}))
                        continue
                    if change['field'] != 'messages': continue
                    if value['metadata']['phone_number_id'] != connection['phone_number_id']: raise DomainError('forbidden', 403)
                    for message in value.get('messages', []):
                        kind = message['type']
                        data = message.get(kind, {})
                        content = data.get('body', data.get('caption', data.get('text', '')))
                        if kind == 'interactive':
                            content = data.get('button_reply', data.get('list_reply', {})).get('title', '')
                        attachments = []
                        if kind in ('image', 'document', 'audio', 'video'):
                            attachments = [{'name': data.get('filename', 'media'), 'media_type': data.get('mime_type', 'application/octet-stream'),
                                            'provider_media_id': data['id'], 'size': 0, 'sha256': data.get('sha256')}]
                        events.append(NormalizedInbound(external_message_id=message['id'], sender_id=e164('+' + message['from'].lstrip('+')),
                            recipient_id=connection['sender_id'], content=content, attachments=attachments,
                            timestamp=datetime.fromtimestamp(int(message['timestamp']), timezone.utc),
                            content_type='attachment' if attachments else 'text', metadata={'provider_type': kind}))
                    for status in value.get('statuses', []):
                        events.append(NormalizedInbound(external_message_id='status:' + status['id'] + ':' + status['status'],
                            sender_id=connection['sender_id'], recipient_id=connection['sender_id'], timestamp=received_at,
                            content_type='status', metadata={'provider_message_id': status['id'], 'status': status['status'],
                            'message_id': status.get('biz_opaque_callback_data'), 'error_code': 'provider_error' if status.get('errors') else None}))
            if not events or len(events) > 50: raise DomainError('invalid_input', 422)
            return events
        except (ValueError, KeyError, TypeError, AttributeError): raise DomainError('invalid_input', 422) from None

    def send_message(self, message, connection, credentials, idempotency_key):
        if self.sender is None: raise DomainError('unconfigured', 503)
        return self.sender(message, connection, credentials, idempotency_key)


class TwilioSMSAdapter(MockMessagingAdapter):
    def __init__(self, sender=None):
        super().__init__('sms')
        self.sender = sender
        self.capability = Capability('twilio', 'LIVE_UNVERIFIED', features=('sms', 'delivery_callbacks', 'unicode'))

    def validate_inbound_event(self, body, headers, connection, credentials):
        try:
            from twilio.request_validator import RequestValidator
        except ImportError: raise DomainError('unconfigured', 503) from None
        try:
            fields = parse_qsl(body.decode(), keep_blank_values=True, max_num_fields=128)
        except (UnicodeError, ValueError): raise DomainError('invalid_input', 422) from None
        if len({key for key, _ in fields}) != len(fields): raise DomainError('invalid_input', 422)
        url = connection['public_origin'].rstrip('/') + connection['_webhook_path']
        if not RequestValidator(credentials['auth_token']).validate(url, dict(fields), headers.get('x-twilio-signature', '')):
            raise DomainError('invalid_signature', 401)

    def normalize_inbound_event(self, body, connection, received_at):
        try:
            fields = dict(parse_qsl(body.decode(), keep_blank_values=True))
        except (ValueError, UnicodeError): raise DomainError('invalid_input', 422) from None
        if fields.get('AccountSid') != connection['account_sid']: raise DomainError('forbidden', 403)
        if 'MessageStatus' in fields:
            if not fields.get('MessageSid'): raise DomainError('invalid_input', 422)
            status = {'queued': 'sent', 'sending': 'sent', 'undelivered': 'failed'}.get(fields['MessageStatus'], fields['MessageStatus'])
            return [NormalizedInbound(external_message_id='status:' + fields['MessageSid'] + ':' + status,
                sender_id=connection['sender_id'], recipient_id=connection['sender_id'], timestamp=received_at, content_type='status',
                metadata={'provider_message_id': fields['MessageSid'], 'status': status,
                          'message_id': connection.get('_message_id'), 'error_code': 'provider_error' if fields.get('ErrorCode') else None})]
        if not fields.get('MessageSid') or not fields.get('From') or not fields.get('To'): raise DomainError('invalid_input', 422)
        self.resolve_channel_connection(connection, fields['To'])
        try: count = int(fields.get('NumMedia', '0'))
        except ValueError: raise DomainError('invalid_input', 422) from None
        if not 0 <= count <= 10: raise DomainError('invalid_input', 422)
        attachments = [{'name': 'media', 'media_type': fields.get('MediaContentType' + str(index), 'application/octet-stream'),
                        'provider_media_id': fields.get('MediaUrl' + str(index), ''), 'size': 0} for index in range(count)]
        return [NormalizedInbound(external_message_id=fields['MessageSid'], sender_id=e164(fields['From']),
            recipient_id=e164(fields['To']), timestamp=received_at, content=fields.get('Body', ''), attachments=attachments)]

    def send_message(self, message, connection, credentials, idempotency_key):
        if self.sender is None: raise DomainError('unconfigured', 503)
        return self.sender(message, connection, credentials, idempotency_key)
