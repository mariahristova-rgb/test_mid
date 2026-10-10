"""Tenant-owned quarantine. Never fetch arbitrary provider URLs or execute attachments."""
import base64
from hashlib import sha256
from pathlib import PurePosixPath
from datetime import timedelta
from .domain import DomainError

ALLOWED = {'text/plain', 'text/csv', 'application/pdf', 'image/png', 'image/jpeg', 'text/calendar'}


class AttachmentStore:
    def __init__(self, store, secrets, clock):
        self.store, self.secrets, self.clock = store, secrets, clock

    def put(self, tenant_id, conversation_id, item):
        self.store.get('conversations', tenant_id, conversation_id)
        name = item.get('name', 'attachment')
        media = item.get('media_type', 'application/octet-stream').split(';')[0].lower()
        if not name or len(name) > 200 or name != PurePosixPath(name).name or '\\' in name or '..' in name or any(ord(c) < 32 for c in name):
            raise DomainError('invalid_input', 422)
        if media not in ALLOWED: raise DomainError('unsupported_attachment', 422)
        data = None
        try: size = int(item.get('size', 0))
        except (ValueError, TypeError): raise DomainError('invalid_input', 422) from None
        if not 0 <= size <= 2_000_000: raise DomainError('invalid_input', 413)
        if item.get('data_base64'):
            try: data = base64.b64decode(item['data_base64'], validate=True)
            except (ValueError, TypeError): raise DomainError('invalid_input', 422) from None
            if len(data) > 2_000_000: raise DomainError('invalid_input', 413)
            magic = {'application/pdf': b'%PDF-', 'image/png': b'\x89PNG\r\n\x1a\n', 'image/jpeg': b'\xff\xd8'}
            if media in magic and not data.startswith(magic[media]): raise DomainError('invalid_input', 422)
            if media.startswith('text/'):
                try: data.decode('utf-8')
                except UnicodeError: raise DomainError('invalid_input', 422) from None
        record = self.store.add('attachments', tenant_id, {'conversation_id': conversation_id, 'name': name,
            'media_type': media, 'size': len(data) if data is not None else size,
            'status': 'quarantined' if data is not None else 'metadata_only',
            'provider_media_id': item.get('provider_media_id'), 'digest': sha256(data).hexdigest() if data is not None else item.get('sha256'),
            'expires_at': (self.clock() + timedelta(days=self.store.tenant(tenant_id)['retention_days'])).isoformat()})
        if data is not None:
            self.secrets.put(tenant_id, 'attachment:' + record['id'], base64.b64encode(data).decode())
        return {'name': name, 'media_type': media, 'size': record['size'], 'storage_key': record['id']}
