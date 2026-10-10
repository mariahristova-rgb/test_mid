"""Persistent reminder queue; transactionally claimed, bounded retries, mock dispatch."""
from datetime import datetime, timedelta, timezone
from .domain import DomainError
from .language import tr, format_date
from .store import now


class ReminderQueue:
    def __init__(self, store, orchestrator):
        self.store, self.orchestrator = store, orchestrator

    def run_due(self, principal, *, at=None):
        principal.require('approve')
        at = at or datetime.now(timezone.utc)
        results = []
        for candidate in self.store.list('jobs', principal.tenant_id):
            if candidate.get('kind') != 'appointment_reminder':
                continue
            with self.store.transaction():
                job = self.store.get('jobs', principal.tenant_id, candidate['id'])
                if job['status'] not in ('pending', 'retry') or datetime.fromisoformat(job['due_at']) > at:
                    continue
                appointment = self.store.get('appointments', principal.tenant_id, job['appointment_id'])
                if appointment['status'] == 'cancelled':
                    self.store.update('jobs', principal.tenant_id, job['id'], {'status': 'cancelled'})
                    continue
                try:
                    conversation = self.store.get('conversations', principal.tenant_id, job['conversation_id'])
                    assistant = self.store.get('assistants', principal.tenant_id, conversation['assistant_id'])
                    if assistant['status'] != 'active' or conversation['channel'] not in assistant['enabled_channels']:
                        raise DomainError('disabled', 409)
                    locale = appointment['locale']
                    template = self.store.find('notification_templates', principal.tenant_id, locale + ':reminder')
                    body = template['body'] if template else tr(locale, 'reminder', date='{date}')
                    text = body.format(date=format_date(appointment['starts_at'], locale, self.store.tenant(principal.tenant_id)['timezone']))
                    if conversation.get('connection_id') and self.orchestrator.messaging:
                        self.orchestrator.messaging.reminder(principal, job, appointment, conversation)
                    else:
                        self.orchestrator.dispatch(principal, assistant, conversation, text, locale, job['id'], at=at)
                    self.store.update('jobs', principal.tenant_id, job['id'], {'status': 'completed', 'completed_at': now()})
                    self.store.audit(principal, 'reminder:dispatched', resource_id=job['id'])
                    results.append({'id': job['id'], 'status': 'completed', 'state': 'MOCK'})
                except DomainError as exc:
                    attempts = job['attempts'] + 1
                    status = 'failed' if attempts >= 3 or exc.code in ('forbidden', 'disabled') else 'retry'
                    self.store.update('jobs', principal.tenant_id, job['id'], {'status': status, 'attempts': attempts,
                                      'error_code': exc.code, 'due_at': (at + timedelta(seconds=30 * attempts)).isoformat()})
                    self.store.audit(principal, 'reminder:failed', resource_id=job['id'], status=exc.code)
                    results.append({'id': job['id'], 'status': status, 'code': exc.code, 'state': 'MOCK'})
        return results
