"""Mock calendar infrastructure. Tenant ownership/transactions use the existing store."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .domain import DomainError, Capability
from .language import parse_date


class MockCalendarProvider:
    capability = Capability('mock-calendar', 'MOCK', features=('availability', 'booking', 'reschedule', 'cancel'))

    def __init__(self, store):
        self.store = store

    def available(self, tenant_id, starts_at, minutes, exclude=None, *, tenant_override=None):
        return bool(self.available_resources(tenant_id, starts_at, minutes, exclude, tenant_override=tenant_override))

    def available_resources(self, tenant_id, starts_at, minutes, exclude=None, *, tenant_override=None):
        start = datetime.fromisoformat(starts_at)
        end = start + timedelta(minutes=minutes)
        tenant = tenant_override or self.store.tenant(tenant_id)
        policy = tenant.get('calendar_policy')
        resources = [None]
        if policy:
            local = start.astimezone(ZoneInfo(tenant['timezone']))
            finish = end.astimezone(ZoneInfo(tenant['timezone']))
            if local.date().isoformat() in policy.get('holidays',[]):return []
            for period in policy.get('unavailable_periods',[]):
                if start<datetime.fromisoformat(period['ends_at'].replace('Z','+00:00')) and datetime.fromisoformat(period['starts_at'].replace('Z','+00:00'))<end:
                    return []
            if (local.weekday() not in policy['weekdays'] or local.date() != finish.date()
                    or local.strftime('%H:%M') < policy['opens'] or finish.strftime('%H:%M') > policy['closes']
                    or minutes != policy['duration_minutes'] or local.minute % policy['slot_minutes'] or local.second or local.microsecond):
                return []
            resources = [resource['id'] for resource in policy['resources']]
        for appointment in self.store.list('appointments', tenant_id):
            if appointment['id'] == exclude or appointment['status'] == 'cancelled':
                continue
            existing = datetime.fromisoformat(appointment['starts_at'])
            if start < existing + timedelta(minutes=appointment['duration_minutes']) and existing < end:
                if appointment.get('dentist_id') is None: return []
                resources = [resource for resource in resources if resource != appointment['dentist_id']]
        return resources

    def day_slots(self, tenant_id, day, minutes, timezone, after, *, tenant_override=None):
        """Explicit synthetic office-hours fixture, never a production calendar assumption."""
        slots = []
        policy = (tenant_override or self.store.tenant(tenant_id)).get('calendar_policy')
        opening, closing, step = 9*60, 17*60, 30
        if policy:
            opening = sum(int(v)*m for v, m in zip(policy['opens'].split(':'), (60,1)))
            closing = sum(int(v)*m for v, m in zip(policy['closes'].split(':'), (60,1)))
            step = policy['slot_minutes']
        for minute in range(opening, closing - minutes + 1, step):
            try:
                start = parse_date(f'{day}T{minute // 60:02d}:{minute % 60:02d}', 'en-US', timezone)
            except DomainError as error:
                if error.code == 'timezone_required':
                    continue  # Do not offer ambiguous/nonexistent DST wall-clock slots.
                raise
            if start > after and self.available(tenant_id, start.isoformat(), minutes, tenant_override=tenant_override): slots.append(start.isoformat())
        return slots

    def create(self, tenant_id, arguments, conversation, timezone):
        with self.store.transaction():
            self.store.get('conversations', tenant_id, conversation['id'])
            resources = self.available_resources(tenant_id, arguments['starts_at'], arguments['duration_minutes'])
            if not resources:
                raise DomainError('conflict', 409)
            allocation = {'dentist_id': resources[0], 'service_id': self.store.tenant(tenant_id)['calendar_policy']['service_id']} if resources[0] else {}
            return self.store.add('appointments', tenant_id, {**arguments, **allocation, 'status': 'confirmed',
                'locale': conversation['active_locale'], 'conversation_id': conversation['id'], 'timezone': timezone})

    def reschedule(self, tenant_id, appointment_id, arguments):
        with self.store.transaction():
            original = self.store.get('appointments', tenant_id, appointment_id)
            resources = self.available_resources(tenant_id, arguments['starts_at'], arguments['duration_minutes'], appointment_id)
            if original['status'] == 'cancelled' or not resources:
                raise DomainError('conflict', 409)
            if resources[0]: arguments = {**arguments, 'dentist_id': resources[0]}
            return self.store.update('appointments', tenant_id, appointment_id, arguments)

    def cancel(self, tenant_id, appointment_id):
        return self.store.update('appointments', tenant_id, appointment_id, {'status': 'cancelled'})
