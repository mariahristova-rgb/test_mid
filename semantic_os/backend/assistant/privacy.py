"""Explicit tenant-admin export and erasure workflows. Financial ledger/audit retention is separate."""
from typing import Literal
from pydantic import Field, model_validator
from .domain import Contract, DomainError
from .store import TABLES


class PrivacyRequest(Contract):
    kind: Literal['conversation', 'contact', 'tenant']
    resource_id: str | None = None
    confirmed: Literal[True]

    @model_validator(mode='after')
    def target(self):
        if self.kind != 'tenant' and not self.resource_id: raise ValueError('Resource required')
        return self


class PrivacyService:
    RequestModel = PrivacyRequest

    def __init__(self, store, messaging, clock): self.store, self.messaging, self.clock = store, messaging, clock

    def export(self, principal, contact_id=None):
        principal.require('configure')
        with self.store.transaction():
            if contact_id:
                contact = self.store.get('contacts', principal.tenant_id, contact_id)
                conversations = [c for c in self.store.list('conversations', principal.tenant_id) if c.get('contact_id') == contact_id]
                data = {'contact': contact, 'conversations': conversations, 'messages': [m for c in conversations for m in self.store.list('messages', principal.tenant_id, c['id'])]}
            else:
                excluded = {'secrets', 'verification_tokens', 'support_grants'}
                data = {'tenant': self.store.tenant(principal.tenant_id),
                    'resources': {table: self.store.list(table, principal.tenant_id) for table in TABLES if table not in excluded}}
            self.store.audit(principal, 'privacy:export', resource_id=contact_id or principal.tenant_id)
            return {'exported_at': self.clock().isoformat(), 'data': data, 'excluded': ['provider_credentials', 'verification_tokens', 'encrypted_media_bytes']}

    def request(self, principal, config):
        principal.require('configure')
        if config.kind != 'tenant': self.store.get('contacts' if config.kind == 'contact' else 'conversations', principal.tenant_id, config.resource_id)
        result = self.store.add('privacy_requests', principal.tenant_id, {'kind': config.kind, 'resource_id': config.resource_id,
            'status': 'pending', 'requested_by': principal.user_id, 'requested_at': self.clock().isoformat()})
        self.store.audit(principal, 'privacy:requested', resource_id=result['id'])
        return result

    def redact_conversation(self, principal, id):
        self.messaging.delete_content(principal, id)
        for message in self.store.list('messages', principal.tenant_id, id):
            self.store.update('messages', principal.tenant_id, message['id'], {key: 'redacted' for key in ('sender', 'sender_id', 'recipient', 'recipient_id', 'external_id', 'external_message_id')})
        for table in ('agent_executions', 'tool_executions', 'approvals'):
            for row in self.store.list(table, principal.tenant_id, id):
                changes = {'arguments': {}, 'outcome': {}, 'result': {}, 'handoff': {}, 'redacted': True}
                if table == 'approvals' and row['status'] == 'pending': changes['status'] = 'cancelled'
                self.store.update(table, principal.tenant_id, row['id'], changes)
        for table in ('appointments', 'follow_up_tasks'):
            for row in self.store.list(table, principal.tenant_id):
                if row.get('conversation_id') == id:
                    self.store.update(table, principal.tenant_id, row['id'], {'contact_name': '', 'title': '', 'redacted': True})
        for table in ('call_sessions', 'voice_transcripts', 'call_participants'):
            for row in self.store.list(table, principal.tenant_id, id):
                self.store.update(table, principal.tenant_id, row['id'], {'caller_identifier': 'redacted', 'identifier': 'redacted', 'transcripts': [], 'last_response': '', 'redacted': True})
        for table, prefix in (('voice_transcripts', 'transcript:'), ('voice_recordings', 'recording:')):
            for row in self.store.list(table, principal.tenant_id, id):
                secret = self.store.find('secrets', principal.tenant_id, prefix + row['id'])
                if secret: self.store.update('secrets', principal.tenant_id, secret['id'], {'encrypted': '', 'state': 'revoked'})
                self.store.update(table, principal.tenant_id, row['id'], {'redacted': True})
        self.store.update('conversations', principal.tenant_id, id, {'remote_sender_id': '', 'remote_recipient_id': '', 'last_email_message_id': '', 'thread_id': ''})

    def execute(self, principal, id):
        principal.require('configure')
        with self.store.transaction():
            request = self.store.get('privacy_requests', principal.tenant_id, id)
            if request['status'] == 'completed': return request
            if any(c['status'] not in ('ended', 'failed', 'transferred') for c in self.store.list('call_sessions', principal.tenant_id)):
                raise DomainError('conflict', 409)
            if request['kind'] == 'conversation': self.redact_conversation(principal, request['resource_id'])
            elif request['kind'] == 'contact':
                contact_id = request['resource_id']
                for conversation in self.store.list('conversations', principal.tenant_id):
                    if conversation.get('contact_id') == contact_id: self.redact_conversation(principal, conversation['id'])
                self.store.update('contacts', principal.tenant_id, contact_id, {'name': '', 'address': '', 'preferred_locale': None,
                    'sms_consent': False, 'whatsapp_consent': False, 'consent_evidence': '', 'evidence': '', 'redacted': True})
                for link in self.store.list('contact_links', principal.tenant_id):
                    if contact_id in (link['first_id'], link['second_id']): self.store.update('contact_links', principal.tenant_id, link['id'], {'evidence': '', 'status': 'revoked'})
            else:
                retained = {'billing_usage', 'billing_customers', 'billing_invoices', 'payment_events', 'subscriptions', 'subscription_items', 'audit_events', 'privacy_requests'}
                # Explicit execution only; never called by startup or retention timers.
                for table in reversed(TABLES):
                    if table not in retained: self.store.db.execute(f'DELETE FROM {table} WHERE tenant_id=?', (principal.tenant_id,))
                tenant = self.store.tenant(principal.tenant_id)
                self.store.update_tenant(principal.tenant_id, {'id': principal.tenant_id, 'name': 'redacted', 'onboarding_state': 'cancelled',
                    'email_verified': False, 'default_locale': tenant['default_locale'], 'timezone': tenant['timezone'], 'retention_days': tenant['retention_days'],
                    'usage_limit': 0, 'recording_enabled': False, 'transcripts_enabled': False})
                subscription = self.store.find('subscriptions', principal.tenant_id, 'current')
                if subscription: self.store.update('subscriptions', principal.tenant_id, subscription['id'], {'status': 'cancelled'})
            result = self.store.update('privacy_requests', principal.tenant_id, id, {'status': 'completed', 'executed_at': self.clock().isoformat(),
                'retained_scope': ['pseudonymous_financial_ledger', 'financial_records', 'audit', 'request_receipt'], 'upstream_erasure_status': 'owner_action_required'})
            self.store.audit(principal, 'privacy:executed', resource_id=id)
            return result
