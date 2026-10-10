"""Signed incoming-call routing, encrypted provider configuration and one-use stream tickets."""
import hashlib
import hmac
import json
import os
import secrets
from datetime import timedelta
from urllib.parse import urlsplit, parse_qsl
from .domain import DomainError, Principal, VoiceConfig
from .providers import MockTelephonyProvider, MockSpeechProvider, e164
from .live_voice import TwilioTelephonyProvider, AzureSpeechProvider, stream_twiml


class TelephonyGateway:
    def __init__(self, store, secret_store, manager):
        self.store, self.secrets, self.manager = store, secret_store, manager
        manager.gateway = self

    def configure(self, principal, data, credentials):
        principal.require('configure')
        assistant = self.store.get('assistants', principal.tenant_id, data['assistant_id'])
        cfg = VoiceConfig.model_validate(assistant.get('voice_settings', {}))
        if 'voice' not in assistant['enabled_channels']:
            raise DomainError('disabled', 409)
        data['phone_number'] = e164(data['phone_number'])
        if cfg.incoming_phone_number and cfg.incoming_phone_number != data['phone_number']:
            raise DomainError('forbidden', 403)
        if data['provider'] == 'twilio':
            if (cfg.telephony_provider, cfg.stt_provider, cfg.tts_provider) != ('twilio', 'azure', 'azure'):
                raise DomainError('invalid_input', 422)
            if any(cfg.voices[locale] not in AzureSpeechProvider.VOICES[locale] for locale in cfg.voices):
                raise DomainError('unsupported_locale', 422)
            TwilioTelephonyProvider(data['account_sid'], credentials['auth_token'])
            AzureSpeechProvider(credentials['speech_key'], data['speech_resource'], data['speech_region'])
            origin = urlsplit(data['public_origin'])
            if origin.scheme != 'https' or not origin.hostname or origin.username or origin.password or origin.path not in ('', '/') or origin.query or origin.fragment:
                raise DomainError('invalid_input', 422)
            if data.get('enable_live') and os.getenv('ASSISTANT_ENABLE_LIVE_VOICE', '') != 'true':
                raise DomainError('unconfigured', 503)
        elif (cfg.telephony_provider, cfg.stt_provider, cfg.tts_provider) != ('mock', 'mock', 'mock'):
            raise DomainError('unconfigured', 503)
        with self.store.transaction():
            if any(c.get('phone_number') == data['phone_number'] and c.get('enabled', True) for c in self.store.list('channel_connections', principal.tenant_id)):
                raise DomainError('conflict', 409)
            record = self.store.add('channel_connections', principal.tenant_id, {**data, 'channel': 'voice',
                'service_user_id': principal.user_id, 'enabled': True,
                'state': 'MOCK' if data['provider'] == 'mock' else 'LIVE_UNVERIFIED'})
            for name, value in credentials.items():
                if value:
                    self.secrets.put(principal.tenant_id, 'voice:' + record['id'] + ':' + name, value)
            self.store.audit(principal, 'telephony:configured', resource_id=record['id'])
            return record

    def services(self, connection):
        self.principal(connection)
        tenant, id = connection['tenant_id'], connection['id']
        if connection['provider'] == 'mock':
            return self.manager.providers.telephony, self.manager.providers.speech, self.manager.providers.speech
        enabled = connection.get('enable_live') and os.getenv('ASSISTANT_ENABLE_LIVE_VOICE', '') == 'true'
        telephony = TwilioTelephonyProvider(connection['account_sid'], self.secrets.get(tenant, 'voice:' + id + ':auth_token'), enabled=enabled)
        speech = AzureSpeechProvider(self.secrets.get(tenant, 'voice:' + id + ':speech_key'),
                                     connection['speech_resource'], connection['speech_region'], enabled=enabled)
        return telephony, speech, speech

    def principal(self, connection):
        user = self.store.get('users', connection['tenant_id'], connection['service_user_id'])
        if not user['enabled'] or not connection.get('enabled', True):
            raise DomainError('forbidden', 403)
        principal = Principal(connection['tenant_id'], user['id'], user['role'], user['subject'])
        principal.require('execute')
        if self.store.entitlements: self.store.entitlements.access(connection['tenant_id'])
        return principal

    def verify(self, tenant_id, connection_id, body, signature):
        connection = self.store.get('channel_connections', tenant_id, connection_id)
        if connection['channel'] != 'voice':
            raise DomainError('forbidden', 403)
        self.principal(connection)
        if connection['provider'] == 'mock':
            key = self.secrets.get(tenant_id, 'voice:' + connection_id + ':webhook_secret')
            expected = hmac.new(key.encode(), body, hashlib.sha256).hexdigest()
            if not signature or not hmac.compare_digest(expected, signature):
                raise DomainError('invalid_signature', 401)
            try:
                payload = json.loads(body)
            except (ValueError, TypeError):
                raise DomainError('invalid_input', 422) from None
        else:
            telephony, _, _ = self.services(connection)
            url = connection['public_origin'].rstrip('/') + '/webhooks/telephony/' + tenant_id + '/' + connection_id
            if not telephony.verify_webhook(url, body, signature):
                raise DomainError('invalid_signature', 401)
            if not connection.get('enable_live') or os.getenv('ASSISTANT_ENABLE_LIVE_VOICE') != 'true':
                raise DomainError('unconfigured', 503)
            fields = dict(parse_qsl(body.decode(), keep_blank_values=True))
            if fields.get('AccountSid') != connection['account_sid']:
                raise DomainError('forbidden', 403)
            payload = {'call_id': fields.get('CallSid'), 'from': fields.get('From'), 'to': fields.get('To'),
                       'status': fields.get('CallStatus', 'ringing'), 'event_id': fields.get('SequenceNumber', 'incoming') + ':' + fields.get('CallStatus', 'ringing')}
        if not isinstance(payload, dict) or set(payload) - {'call_id', 'from', 'to', 'status', 'event_id'}:
            raise DomainError('invalid_input', 422)
        if not all(isinstance(payload.get(key), str) and 0 < len(payload[key]) <= 200 for key in ('call_id', 'from', 'to', 'status', 'event_id')):
            raise DomainError('invalid_input', 422)
        if e164(payload['to']) != connection['phone_number']:
            raise DomainError('forbidden', 403)
        payload['from'] = e164(payload['from'])
        return connection, payload

    def incoming(self, tenant_id, connection_id, body, signature):
        connection, payload = self.verify(tenant_id, connection_id, body, signature)
        principal = self.principal(connection)
        with self.store.transaction():
            external_key = 'call:' + connection_id + ':' + payload['call_id']
            existing = self.store.find('call_sessions', tenant_id, external_key)
            if existing:
                if payload['status'] in ('completed', 'failed', 'busy', 'no-answer', 'canceled'):
                    return self.manager.finish(principal, existing['id'], 'failed' if payload['status'] == 'failed' else 'ended', 'provider_error' if payload['status'] == 'failed' else None)
                return existing
            if payload['status'] not in ('ringing', 'initiated', 'in-progress'):
                raise DomainError('invalid_transition', 409)
            config = VoiceConfig.model_validate(self.store.get('assistants', tenant_id, connection['assistant_id']).get('voice_settings', {}))
            call = self.manager.start(principal, connection['assistant_id'], None, caller=payload['from'],
                                      provider_call_id=payload['call_id'], connection_id=connection_id, external_key=external_key)
            return call

    def ticket(self, principal, call_id, *, twilio=False):
        principal.require('execute')
        call = self.store.get('call_sessions', principal.tenant_id, call_id)
        if call['status'] in ('ended', 'transferred', 'failed'):
            raise DomainError('invalid_transition', 409)
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode()).hexdigest()
        self.store.add('voice_tickets', principal.tenant_id, {'conversation_id': call['conversation_id'],
            'call_id': call_id, 'user_id': principal.user_id, 'expires_at': (self.manager.clock() + timedelta(seconds=60)).isoformat(),
            'used': False, 'twilio': twilio}, external_key=digest)
        # Ticket is returned once, never persisted in plaintext or placed in a URL.
        return token

    def consume_ticket(self, token):
        if not isinstance(token, str) or len(token) > 100:
            raise DomainError('unauthorized', 401)
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.store.transaction():
            row = self.store.db.execute('SELECT tenant_id,data FROM voice_tickets WHERE external_key=?', (digest,)).fetchone()
            if not row:
                raise DomainError('unauthorized', 401)
            record = json.loads(row['data'])
            from datetime import datetime
            if record['used'] or datetime.fromisoformat(record['expires_at']) < self.manager.clock():
                raise DomainError('unauthorized', 401)
            user = self.store.get('users', row['tenant_id'], record['user_id'])
            if not user['enabled']:
                raise DomainError('forbidden', 403)
            principal = Principal(row['tenant_id'], user['id'], user['role'], user['subject'])
            principal.require('execute')
            call = self.store.get('call_sessions', row['tenant_id'], record['call_id'])
            assistant = self.store.get('assistants', row['tenant_id'], call['assistant_id'])
            if assistant['status'] != 'active' or 'voice' not in assistant['enabled_channels']:
                raise DomainError('disabled', 409)
            if call.get('connection_id'):
                self.principal(self.store.get('channel_connections', row['tenant_id'], call['connection_id']))
            if call['status'] in ('ended', 'transferred', 'failed'):
                raise DomainError('invalid_transition', 409)
            self.store.update('voice_tickets', row['tenant_id'], record['id'], {'used': True})
            return principal, call, record['twilio']
