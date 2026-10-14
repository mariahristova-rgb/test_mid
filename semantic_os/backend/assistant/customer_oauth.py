"""Customer OAuth lifecycle using existing contracts, tenant Store and encrypted vault.

Disabled unless a server supplies reviewed app configs, HTTP and identity verification.
No credentials are accepted from customers and no default network transport exists.
"""
import base64
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import json
import secrets
from urllib.parse import urlencode
from .connector_adapters import PROFILES, required_scopes
from .connector_contracts import PlatformOAuthApplication, CustomerConnectionConfig
from .domain import DomainError


class GoogleCustomerIdentity:
    """Verified customer identity; deliberately independent of the owner allowlist."""
    def __init__(self, jwks):
        self.jwks = jwks

    def __call__(self, provider, tokens, client_id, nonce):
        import jwt
        if provider != 'google':
            raise DomainError('unconfigured', 503)
        try:
            token = tokens['id_token']
            if not isinstance(token, str) or len(token) > 16000:
                raise ValueError()
            key = self.jwks.get_signing_key_from_jwt(token).key
            claims = jwt.decode(token, key, algorithms=['RS256'], audience=client_id,
                issuer=['https://accounts.google.com', 'accounts.google.com'],
                options={'require': ['exp', 'iat', 'sub', 'nonce', 'email_verified'], 'strict_aud': True}, leeway=30)
            if claims['email_verified'] is not True or not isinstance(claims['sub'], str) or not claims['sub']:
                raise ValueError()
            if not isinstance(claims['nonce'], str) or not hmac.compare_digest(claims['nonce'], nonce):
                raise ValueError()
            return claims['sub']
        except (KeyError, TypeError, ValueError, jwt.PyJWTError):
            raise DomainError('oauth_account_mismatch', 403) from None


class CustomerOAuthService:
    def __init__(self, store, vault, *, applications=None, http=None,
                 platform_secret=None, verify_identity=None, clock=None):
        self.store, self.vault = store, vault
        self.apps = {a.provider: a for a in (applications or [])}
        if any(not isinstance(a, PlatformOAuthApplication) for a in self.apps.values()):
            raise ValueError('Reviewed app contracts required')
        self.http, self.platform_secret, self.verify_identity = http, platform_secret, verify_identity
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def guard(self, actor, provider=None, recovery=False):
        actor.require('configure')
        if not self.http or not self.platform_secret or not self.verify_identity or not self.vault.cipher:
            raise DomainError('unconfigured', 503)
        if provider and (provider not in self.apps or hasattr(self.verify_identity, 'supports') and not self.verify_identity.supports(provider)):
            raise DomainError('unconfigured', 503)
        if self.store.entitlements:
            self.store.entitlements.access(actor.tenant_id, recovery=recovery)

    def row(self, actor, identity):
        row = self.store.get('operations_events', actor.tenant_id, identity)
        if row.get('kind') != 'customer_connection':
            raise DomainError('not_found', 404)
        return row

    @staticmethod
    def project(row):
        return {k: row.get(k) for k in ('id', 'provider', 'actions', 'resource_ids',
                'state', 'revision', 'verification', 'failure_code', 'booking_enabled')}

    def create(self, actor, config: CustomerConnectionConfig):
        self.guard(actor, config.provider)
        available=next(item['actions'] for item in self.catalog(actor) if item['provider']==config.provider)
        if set(config.actions)-set(available):
            raise DomainError('tool_denied',403)
        if config.revision != 1 or config.resource_ids:
            raise DomainError('invalid_input', 422)  # Resources must be discovered after authorization.
        with self.store.transaction():
            if self.store.entitlements:
                self.store.entitlements.check_connector(actor.tenant_id, config.provider, creating=True)
            row = self.store.add('operations_events', actor.tenant_id, {
                'kind': 'customer_connection', **config.model_dump(), 'state': 'disconnected',
                'verification': 'NOT_TESTED', 'failure_code': None})
            self.store.audit(actor, 'connector:customer_created', resource_id=row['id'])
        return self.project(row)

    def list(self, actor):
        actor.require('configure')
        return [self.project(r) for r in self.store.list('operations_events', actor.tenant_id)
                if r.get('kind') == 'customer_connection']

    def catalog(self, actor):
        actor.require('configure')
        capabilities={'google':['availability','create'],'outlook':['availability'],'calendly':['availability','scheduled_events'],'hubspot':['contact_read']}
        return [{'provider': provider, 'configured': provider in self.apps and bool(
                    self.http and self.platform_secret and self.verify_identity and self.vault.cipher)
                    and (not isinstance(self.verify_identity, GoogleCustomerIdentity) or provider == 'google')
                    and (not hasattr(self.verify_identity, 'supports') or self.verify_identity.supports(provider)),
                 'actions': capabilities[provider], 'verification': 'NOT_TESTED'}
                for provider in PROFILES]

    def start(self, actor, identity, revision):
        self.guard(actor)
        with self.store.transaction():
            row = self.row(actor, identity)
            self.guard(actor, row['provider'])
            if row['revision'] != revision or row.get('refresh_claim'):
                raise DomainError('conflict', 409)
            if row.get('failure_code') == 'delivery_unknown':
                raise DomainError('delivery_unknown', 409)
            if self.store.entitlements:
                self.store.entitlements.check_connector(actor.tenant_id, row['provider'])
            state, binding, verifier, nonce = [secrets.token_urlsafe(32) for _ in range(4)]
            app = self.apps[row['provider']]
            row = self.store.update('operations_events', actor.tenant_id, identity, {
                'state': 'authorization_pending', 'revision': revision + 1, 'verification': 'NOT_TESTED'})
            event = self.store.add('operations_events', actor.tenant_id, {
                'kind': 'customer_oauth_state', 'connection_id': identity, 'revision': row['revision'],
                'subject': actor.subject, 'user_id': actor.user_id, 'provider': row['provider'],
                'app_hash': sha256(app.model_dump_json().encode()).hexdigest(), 'nonce': nonce,
                'binding_hash': sha256(binding.encode()).hexdigest(), 'state': 'pending',
                'expires_at': (self.clock() + timedelta(minutes=10)).isoformat()},
                external_key='customer-oauth:' + sha256(state.encode()).hexdigest())
            self.vault.put(actor.tenant_id, 'customer:verifier:' + event['id'], verifier, actor)
        params = {'client_id': app.client_id, 'redirect_uri': app.redirect_uri, 'response_type': 'code',
                  'scope': ' '.join(required_scopes(row['provider'], row['actions'])), 'state': state,
                  'nonce': nonce}
        if PROFILES[row['provider']]['pkce']:
            params.update(code_challenge_method='S256', code_challenge=base64.urlsafe_b64encode(
                sha256(verifier.encode()).digest()).decode().rstrip('='))
        if row['provider'] == 'google':
            params.update(access_type='offline', prompt='consent')
        return {'authorization_url': PROFILES[row['provider']]['authorize'] + '?' + urlencode(params),
                'binding': binding, 'state': state, 'revision': row['revision']}

    def validate_tokens(self, row, tokens):
        scope = tokens.get('scope')
        if row['provider'] == 'hubspot' and isinstance(tokens.get('scopes'), list) and all(isinstance(v, str) for v in tokens['scopes']):
            scope = ' '.join(tokens['scopes'])
            tokens = {**tokens, 'scope': scope}
        if not isinstance(scope, str) or not set(required_scopes(row['provider'], row['actions'])) <= set(scope.split()):
            raise DomainError('oauth_denied', 403)
        if not all(isinstance(tokens.get(k), str) and tokens[k] for k in ('access_token', 'refresh_token')):
            raise DomainError('oauth_denied', 403)
        expiry = tokens.get('expires_in')
        if isinstance(expiry, bool) or not isinstance(expiry, int) or not 0 < expiry <= 86400:
            raise DomainError('oauth_denied', 403)
        return {**tokens, 'expires_at': (self.clock() + timedelta(seconds=expiry)).isoformat()}

    def exchange(self, row, data):
        app = self.apps[row['provider']]
        response = self.http.request('POST', PROFILES[row['provider']]['token'], data={
            **data, 'client_id': app.client_id, 'client_secret': self.platform_secret(app.secret_reference)})
        if response.status_code != 200:
            raise DomainError('oauth_denied', 403)
        return response.json()

    def complete(self, actor, identity, provider, state, binding, code, *, refused=False):
        self.guard(actor, provider)
        if not refused and (not isinstance(code, str) or not 1 <= len(code) <= 4096):
            raise DomainError('invalid_input', 422)
        with self.store.transaction():
            event = self.store.find('operations_events', actor.tenant_id,
                                   'customer-oauth:' + sha256(state.encode()).hexdigest())
            row = self.row(actor, identity)
            app = self.apps[provider]
            if not event or event.get('kind') != 'customer_oauth_state' or any((
                event['state'] != 'pending', event['connection_id'] != identity,
                event['subject'] != actor.subject, event['user_id'] != actor.user_id,
                event['provider'] != provider, row['provider'] != provider,
                event['revision'] != row['revision'], self.clock().isoformat() >= event['expires_at'],
                event['app_hash'] != sha256(app.model_dump_json().encode()).hexdigest(),
                not hmac.compare_digest(event['binding_hash'], sha256(binding.encode()).hexdigest()))):
                raise DomainError('unauthorized', 401)
            if self.store.entitlements:
                self.store.entitlements.check_connector(actor.tenant_id, provider)
            self.store.update('operations_events', actor.tenant_id, event['id'], {'state': 'consumed'})
            if refused:
                row=self.store.update('operations_events',actor.tenant_id,identity,{'state':'reauthorization_required','revision':row['revision']+1,'failure_code':'oauth_denied','verification':'NOT_TESTED'})
                self.store.audit(actor,'connector:customer_authorization_refused',resource_id=identity)
                return self.project(row)
        data = {'grant_type': 'authorization_code', 'code': code, 'redirect_uri': app.redirect_uri}
        if PROFILES[provider]['pkce']:
            data['code_verifier'] = self.vault.get(actor.tenant_id, 'customer:verifier:' + event['id'], actor)
        tokens = self.exchange(row, data)
        if not isinstance(tokens, dict) or not all(isinstance(tokens.get(k), str) and tokens[k] for k in ('access_token', 'refresh_token')):
            raise DomainError('oauth_denied', 403)
        # Server-injected verifier must validate signature/issuer/audience/nonce or
        # provider introspection, never trust unverified JWTs or customer identity input.
        account = self.verify_identity(provider, tokens, app.client_id, event['nonce'])
        if not isinstance(account, str) or not account or len(account) > 500:
            raise DomainError('oauth_account_mismatch', 403)
        tokens = self.validate_tokens(row, tokens)
        with self.store.transaction():
            if self.row(actor, identity) != row:
                raise DomainError('conflict', 409)
            self.vault.put(actor.tenant_id, 'customer:tokens:' + identity, json.dumps(tokens), actor)
            self.vault.put(actor.tenant_id, 'customer:account:' + identity, account, actor)
            row = self.store.update('operations_events', actor.tenant_id, identity, {
                'state': 'connected_unverified', 'revision': row['revision'] + 1, 'failure_code': None})
            self.store.audit(actor, 'connector:customer_authorized', resource_id=identity)
        return self.project(row)

    def token(self, actor, identity):
        self.guard(actor)
        with self.store.transaction():
            row = self.row(actor, identity)
            if row['state'] not in ('connected_unverified', 'verified'):
                raise DomainError('unconfigured', 503)
            if self.store.entitlements:
                self.store.entitlements.check_connector(actor.tenant_id, row['provider'])
            tokens = json.loads(self.vault.get(actor.tenant_id, 'customer:tokens:' + identity, actor))
            if row.get('refresh_claim'):
                raise DomainError('conflict', 409)
            if datetime.fromisoformat(tokens['expires_at']) > self.clock() + timedelta(seconds=60):
                return tokens['access_token']
            claim = secrets.token_urlsafe(24)
            self.store.update('operations_events', actor.tenant_id, identity, {'refresh_claim': claim})
        # Durable claim is committed before I/O; another Store/process cannot refresh
        # the same grant. A crashed refresh requires explicit reauthorization.
        try:
            fresh = self.exchange(row, {'grant_type': 'refresh_token', 'refresh_token': tokens['refresh_token']})
            updated={**tokens,**fresh}
            if hasattr(self.verify_identity,'refresh'):
                account=self.vault.get(actor.tenant_id,'customer:account:'+identity,actor)
                self.verify_identity.refresh(row['provider'],updated,self.apps[row['provider']].client_id,account)
            updated = self.validate_tokens(row, updated)
        except Exception:
            with self.store.transaction():
                current = self.row(actor, identity)
                if current.get('refresh_claim') == claim:
                    self.store.update('operations_events', actor.tenant_id, identity, {
                        'state': 'reauthorization_required', 'refresh_claim': None,
                        'revision': current['revision'] + 1, 'failure_code': 'oauth_denied'})
            raise DomainError('oauth_denied', 403) from None
        with self.store.transaction():
            current = self.row(actor, identity)
            if current.get('refresh_claim') != claim or current['revision'] != row['revision']:
                raise DomainError('conflict', 409)
            self.vault.put(actor.tenant_id, 'customer:tokens:' + identity, json.dumps(updated), actor)
            self.store.update('operations_events', actor.tenant_id, identity, {'refresh_claim': None})
        return updated['access_token']

    def disconnect(self, actor, identity, revision):
        actor.require('configure')
        if self.store.entitlements:
            self.store.entitlements.access(actor.tenant_id, recovery=True)
        with self.store.transaction():
            row = self.row(actor, identity)
            if row['revision'] != revision:
                raise DomainError('conflict', 409)
            for name in ('customer:tokens:'+identity,'customer:account:'+identity,'customer:resources:'+identity):
                secret=self.store.find('secrets',actor.tenant_id,name)
                if secret:
                    self.vault.revoke(actor,secret['id'])
            row = self.store.update('operations_events', actor.tenant_id, identity, {
                'state': 'disconnected', 'revision': revision + 1, 'refresh_claim': None,
                'verification': 'NOT_TESTED', 'booking_enabled': False})
            self.store.audit(actor, 'connector:customer_disconnected', resource_id=identity)
        return self.project(row)

    def callback(self, provider, state, code, binding, *, refused=False):
        # Opaque state is the only global lookup. No tenant/subject is accepted from
        # the browser; recover the existing membership and recheck configure rights.
        rows = self.store.db.execute(
            "SELECT data FROM operations_events WHERE external_key=? AND json_extract(data,'$.kind')='customer_oauth_state'",
            ('customer-oauth:' + sha256(state.encode()).hexdigest(),)).fetchall()
        if len(rows) != 1:
            raise DomainError('unauthorized', 401)
        event = json.loads(rows[0]['data'])
        actor = self.store.principal(event['subject'], event['tenant_id'])
        return self.complete(actor, event['connection_id'], provider, state, binding, code, refused=refused)

    def resources(self, actor, identity):
        from .connector_adapters import ProviderAdapter,ProductionProviderAdapter,ProductionProviderHTTP
        row = self.row(actor, identity)
        if isinstance(self.http,ProductionProviderHTTP):
            found=ProductionProviderAdapter(row['provider'],self.http).resources(self.token(actor,identity),account_id=self.vault.get(actor.tenant_id,'customer:account:'+identity,actor))
            mapping={'resource_'+sha256((identity+'|'+item['id']).encode()).hexdigest()[:32]:item for item in found}
            self.vault.put(actor.tenant_id,'customer:resources:'+identity,json.dumps(mapping),actor)
            return [{'id':reference,'writable':item['writable'],'ordinal':index+1,'primary':item.get('primary',False)} for index,(reference,item) in enumerate(mapping.items())]
        return ProviderAdapter(row['provider'], self.http).resources(self.token(actor, identity))

    def resolve_resource(self, actor, row, reference):
        from .connector_adapters import ProductionProviderHTTP
        if not isinstance(self.http,ProductionProviderHTTP):
            return reference
        mapping=json.loads(self.vault.get(actor.tenant_id,'customer:resources:'+row['id'],actor))
        if reference not in mapping:
            raise DomainError('forbidden',403)
        return mapping[reference]['id']

    def select_resources(self, actor, identity, revision, resources):
        from .connector_adapters import OfflineProviderHTTP
        self.guard(actor)
        row = self.row(actor, identity)
        if row['revision'] != revision:
            raise DomainError('conflict', 409)
        if not 1 <= len(resources) <= 8 or len(set(resources)) != len(resources):
            raise DomainError('invalid_input', 422)
        discovered = {r['id']: r for r in self.resources(actor, identity)}
        writing = bool(set(row['actions']) & {'create', 'reschedule', 'cancel'})
        if any(r not in discovered or (writing and not discovered[r]['writable']) for r in resources):
            raise DomainError('forbidden', 403)
        with self.store.transaction():
            if self.row(actor, identity) != row:
                raise DomainError('conflict', 409)
            row = self.store.update('operations_events', actor.tenant_id, identity, {
                'resource_ids': resources, 'revision': revision + 1,
                'verification': 'OFFLINE_PASS' if isinstance(self.http, OfflineProviderHTTP) else 'NOT_TESTED'})
            self.store.audit(actor, 'connector:customer_resource_selected', resource_id=identity)
        return self.project(row)


def register_customer_oauth(app, service, actor):
    from fastapi import Depends, Request, Response
    from pydantic import Field
    from .domain import Contract, Principal

    class Revision(Contract):
        revision: int = Field(ge=1)

    class ResourceSelection(Revision):
        resource_ids: list[str] = Field(min_length=1, max_length=8)

    @app.get('/api/customer-connectors')
    def catalog(principal: Principal = Depends(actor)):
        return service.catalog(principal)

    @app.get('/api/customer-connectors/connections')
    def connections(principal: Principal = Depends(actor)):
        return service.list(principal)

    @app.post('/api/customer-connectors/connections')
    def create(payload: CustomerConnectionConfig, principal: Principal = Depends(actor)):
        return service.create(principal, payload)

    @app.post('/api/customer-connectors/connections/{identity}/authorize')
    def authorize(identity: str, payload: Revision, response: Response, principal: Principal = Depends(actor)):
        started = service.start(principal, identity, payload.revision)
        provider = service.row(principal, identity)['provider']
        path = '/backend/api/connectors/oauth/' + provider + '/callback'
        response.set_cookie('customer-oauth-' + provider, started['binding'], secure=True,
                            httponly=True, samesite='lax', max_age=600, path=path)
        return {'authorization_url': started['authorization_url'], 'revision': started['revision']}

    @app.get('/api/connectors/oauth/{provider}/callback')
    def callback(provider: str, state: str, request: Request, code: str | None = None, error: str | None = None):
        from fastapi.responses import RedirectResponse
        from urllib.parse import urlsplit
        if provider not in PROFILES or provider not in service.apps or len(state) > 200 or code and len(code) > 4096:
            raise DomainError('invalid_input', 422)
        if error:
            # Refusal never installs a grant. A fresh authorization can replace the
            # pending revision; no provider error text or OAuth material is echoed.
            service.callback(provider,state,None,request.cookies.get('customer-oauth-' + provider,''),refused=True)
            outcome = 'denied'
        else:
            service.callback(provider, state, code, request.cookies.get('customer-oauth-' + provider, ''))
            outcome = 'connected'
        origin = urlsplit(service.apps[provider].redirect_uri)
        response = RedirectResponse(origin.scheme+'://'+origin.netloc+'/integrations?connection='+outcome, status_code=303)
        response.delete_cookie('customer-oauth-' + provider,
                               path='/backend/api/connectors/oauth/' + provider + '/callback', secure=True, httponly=True)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    @app.post('/api/customer-connectors/connections/{identity}/disconnect')
    def disconnect(identity: str, payload: Revision, principal: Principal = Depends(actor)):
        return service.disconnect(principal, identity, payload.revision)

    @app.get('/api/customer-connectors/connections/{identity}/resources')
    def resources(identity: str, principal: Principal = Depends(actor)):
        return service.resources(principal, identity)

    @app.put('/api/customer-connectors/connections/{identity}/resources')
    def select_resources(identity: str, payload: ResourceSelection, principal: Principal = Depends(actor)):
        return service.select_resources(principal, identity, payload.revision, payload.resource_ids)
