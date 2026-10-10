"""Infrastructure security: encrypted tenant secrets and local/verified identity."""
from hashlib import sha256
import hmac
import os
from cryptography.fernet import Fernet, MultiFernet, InvalidToken
from .domain import DomainError, Principal
from .store import now


class TenantSecretStore:
    def __init__(self, store, key=''):
        self.store = store
        self.cipher = MultiFernet([Fernet(k.strip().encode()) for k in key.split(',')]) if key else None

    def put(self, tenant_id, name, value, principal=None):
        if principal:
            principal.require('configure')
            if principal.tenant_id != tenant_id: raise DomainError('forbidden', 403)
        if self.cipher is None:
            raise DomainError('unconfigured', 503)
        encrypted = self.cipher.encrypt(value.encode()).decode()
        existing = self.store.find('secrets', tenant_id, name)
        if existing:
            record = self.store.update('secrets', tenant_id, existing['id'], {'encrypted': encrypted, 'state': 'active',
                'version': existing.get('version', 1) + 1, 'rotated_at': now()})
        else:
            record = self.store.add('secrets', tenant_id, {'name': name, 'encrypted': encrypted, 'state': 'active', 'version': 1}, external_key=name)
        self.store.audit(principal or Principal(tenant_id, 'secret-service', 'operator', 'secret-service'), 'credential:written', resource_id=record['id'])

    def get(self, tenant_id, name, principal=None):
        if principal:
            principal.require('configure')
            if principal.tenant_id != tenant_id: raise DomainError('forbidden', 403)
        if self.cipher is None:
            raise DomainError('unconfigured', 503)
        record = self.store.find('secrets', tenant_id, name)
        if record is None or record.get('state') == 'revoked' or not record.get('encrypted'):
            raise DomainError('unconfigured', 503)
        try: value = self.cipher.decrypt(record['encrypted'].encode()).decode()
        except InvalidToken: raise DomainError('unconfigured', 503) from None
        self.store.audit(principal or Principal(tenant_id, 'secret-service', 'operator', 'secret-service'), 'credential:read', resource_id=record['id'])
        return value

    def revoke(self, principal, id):
        principal.require('configure')
        record = self.store.get('secrets', principal.tenant_id, id)
        result = self.store.update('secrets', principal.tenant_id, id, {'encrypted': '', 'state': 'revoked', 'revoked_at': now()})
        self.store.audit(principal, 'credential:revoked', resource_id=id)
        return {'id': result['id'], 'name': record['name'], 'state': 'revoked'}

    def rotate_keyring(self, principal):
        principal.require('configure')
        if not self.cipher: raise DomainError('unconfigured', 503)
        with self.store.transaction():
            for record in self.store.list('secrets', principal.tenant_id):
                if record.get('encrypted') and record.get('state') != 'revoked':
                    try: rotated = self.cipher.rotate(record['encrypted'].encode()).decode()
                    except InvalidToken: raise DomainError('unconfigured', 503) from None
                    self.store.update('secrets', principal.tenant_id, record['id'], {'encrypted': rotated, 'key_rotated_at': now()})
            self.store.audit(principal, 'credential:keyring_rotated')
        return {'status': 'rotated'}


class IdentityService:
    def __init__(self, store, *, demo_enabled=False, demo_token='', verifier=None):
        if demo_enabled and not demo_token:
            raise RuntimeError('Explicit demo credentials are required.')
        if demo_enabled and os.getenv('ASSISTANT_ENV', 'development') in ('production', 'staging'):
            raise RuntimeError('Demo authentication is prohibited in production.')
        self.store, self.demo_enabled, self.demo_token, self.verifier = store, demo_enabled, demo_token, verifier
        self.demo_hosts=('127.0.0.1','::1','testclient')
        proxy=os.getenv('ASSISTANT_DEMO_PROXY_IP','')
        if proxy and demo_enabled:
            from ipaddress import ip_address
            address=ip_address(proxy)
            if not address.is_private or address.is_unspecified or address.is_link_local:
                raise RuntimeError('Explicit private demo proxy required')
            self.demo_hosts=(*self.demo_hosts,proxy)

    def authenticate(self, authorization, tenant_id, client_host):
        subject = self.verify_identity(authorization, client_host).subject
        try: return self.store.principal(subject, tenant_id)
        except DomainError:
            import json
            from .store import uid
            from .observability import correlation_id
            with self.store.transaction():
                self.store.db.execute('INSERT INTO platform_audit VALUES(?,?,?)', (uid(), json.dumps({'action': 'security:tenant_access_denied',
                    'subject_hash': sha256(subject.encode()).hexdigest(), 'tenant_hash': sha256(tenant_id.encode()).hexdigest(),
                    'correlation_id': correlation_id.get()}), now()))
            raise

    def verify_identity(self, authorization, client_host):
        scheme, _, token = (authorization or '').partition(' ')
        if scheme.lower() != 'bearer' or not token:
            raise DomainError('unauthorized', 401)
        if self.demo_enabled and hmac.compare_digest(sha256(token.encode()).digest(), sha256(self.demo_token.encode()).digest()):
            if client_host not in self.demo_hosts:
                raise DomainError('forbidden', 403)
            subject = 'demo-admin'
            from ..api.auth0_auth import AuthenticatedSubject
            return AuthenticatedSubject('MOCK', subject)
        elif self.verifier:
            return self.verifier.verify(authorization)
        else:
            raise DomainError('unauthorized', 401)
