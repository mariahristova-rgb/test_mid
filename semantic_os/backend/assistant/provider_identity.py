"""Provider identities verified server-side; no customer-supplied account claims."""
import hmac
from uuid import UUID
from .customer_oauth import GoogleCustomerIdentity
from .connector_adapters import PROFILES
from .domain import DomainError


class ProviderIdentityVerifier:
    def __init__(self, http, platform_secret, *, google_jwks=None, outlook_jwks=None, outlook_tenants=()):
        self.http, self.platform_secret = http, platform_secret
        self.google_jwks, self.outlook_jwks = google_jwks, outlook_jwks
        self.outlook_tenants = set(outlook_tenants)

    def supports(self, provider):
        return bool(self.google_jwks) if provider == 'google' else bool(self.outlook_jwks and self.outlook_tenants) if provider == 'outlook' else bool(self.http and self.platform_secret) if provider in ('calendly', 'hubspot') else False

    def __call__(self, provider, tokens, client_id, nonce):
        if provider == 'google':
            if not self.google_jwks:
                raise DomainError('unconfigured', 503)
            return GoogleCustomerIdentity(self.google_jwks)(provider, tokens, client_id, nonce)
        if provider == 'outlook':
            return self.outlook(tokens, client_id, nonce)
        if provider == 'calendly':
            response = self.http.request('GET', PROFILES[provider]['identity'][1],
                headers={'Authorization': 'Bearer ' + tokens['access_token']})
            if response.status_code != 200:
                raise DomainError('oauth_account_mismatch', 403)
            uri = response.json().get('resource', {}).get('uri', '')
            prefix = 'https://api.calendly.com/users/'
            try:
                if not uri.startswith(prefix) or str(UUID(uri[len(prefix):])) != uri[len(prefix):].lower():
                    raise ValueError()
            except (ValueError, AttributeError):
                raise DomainError('oauth_account_mismatch', 403) from None
            return uri
        if provider == 'hubspot':
            response = self.http.request('POST', PROFILES[provider]['identity'][1], data={
                'client_id': client_id, 'client_secret': self.platform_secret('platform:oauth:hubspot:client_secret'),
                'token_type_hint': 'access_token', 'access_token': tokens['access_token']})
            if response.status_code != 200:
                raise DomainError('oauth_account_mismatch', 403)
            account = response.json()
            if (account.get('active') is not True or account.get('client_id') != client_id
                    or account.get('token_use') != 'access_token' or type(account.get('hub_id')) is not int
                    or account['hub_id'] <= 0):
                raise DomainError('oauth_account_mismatch', 403)
            if not isinstance(account.get('scopes'), list) or not all(isinstance(v, str) for v in account['scopes']):
                raise DomainError('oauth_denied', 403)
            tokens['scope'] = ' '.join(account['scopes'])
            tokens['scopes'] = account['scopes']
            return str(account['hub_id'])
        raise DomainError('unconfigured', 503)

    def outlook(self, tokens, client_id, nonce):
        import jwt
        if not self.outlook_jwks or not self.outlook_tenants:
            raise DomainError('unconfigured', 503)
        try:
            token = tokens['id_token']
            if not isinstance(token, str) or len(token) > 16000:
                raise ValueError()
            hint = jwt.decode(token, options={'verify_signature': False})
            tenant = str(UUID(hint['tid']))
            if tenant not in self.outlook_tenants:
                raise ValueError()
            # The unverified hint selects only a preapproved issuer; it does not
            # authorize an identity or select an arbitrary JWKS endpoint.
            key = self.outlook_jwks.get_signing_key_from_jwt(token).key
            claims = jwt.decode(token, key, algorithms=['RS256'], audience=client_id,
                issuer='https://login.microsoftonline.com/' + tenant + '/v2.0',
                options={'require': ['exp', 'iat', 'sub', 'oid', 'tid', 'nonce'], 'strict_aud': True}, leeway=30)
            if claims['tid'] != tenant or not isinstance(claims['sub'], str) or not claims['sub']:
                raise ValueError()
            if not isinstance(claims['nonce'], str) or not hmac.compare_digest(claims['nonce'], nonce):
                raise ValueError()
            return tenant + ':' + str(UUID(claims['oid']))
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            raise DomainError('oauth_account_mismatch', 403) from None

    def refresh(self,provider,tokens,client_id,expected_account):
        if provider=='hubspot':
            actual=self(provider,tokens,client_id,'')
        elif provider=='calendly':
            actual=self(provider,tokens,client_id,'')
        elif provider in ('google','outlook'):
            response=self.http.request('GET',PROFILES[provider]['identity'][1],headers={'Authorization':'Bearer '+tokens['access_token']})
            if response.status_code!=200:
                raise DomainError('oauth_account_mismatch',403)
            account=response.json()
            if provider=='google':
                if account.get('email_verified') is not True:
                    raise DomainError('oauth_account_mismatch',403)
                actual=account.get('sub')
            else:
                try:
                    actual=expected_account.split(':',1)[0]+':'+str(UUID(account['id']))
                except (KeyError,ValueError,TypeError):
                    raise DomainError('oauth_account_mismatch',403) from None
        else:
            raise DomainError('unconfigured',503)
        if not isinstance(actual,str) or not hmac.compare_digest(actual,expected_account):
            raise DomainError('oauth_account_mismatch',403)
        return actual
