"""Operator-managed OAuth activation; customer inputs never configure app secrets."""
import json
import os
from .connector_contracts import PlatformOAuthApplication
from .connector_adapters import ProductionProviderHTTP
from .provider_identity import ProviderIdentityVerifier


def customer_oauth_environment():
    if os.getenv('ASSISTANT_CUSTOMER_OAUTH_ENABLED') != 'true':
        return {}
    raw = os.getenv('ASSISTANT_CUSTOMER_OAUTH_APPLICATIONS', '')
    if not raw or len(raw) > 20000:
        raise RuntimeError('Reviewed customer OAuth application configuration required')
    data = json.loads(raw)
    if not isinstance(data, list) or not 1 <= len(data) <= 4:
        raise RuntimeError('Invalid platform app catalog')
    apps = [PlatformOAuthApplication.model_validate(value) for value in data]
    if len({app.provider for app in apps}) != len(apps):
        raise RuntimeError('Duplicate platform provider')
    http = ProductionProviderHTTP([app.provider for app in apps], approved=True)
    from .self_hosted import deployment_secret
    def secret(reference):
        provider = next((app.provider for app in apps if app.secret_reference == reference), None)
        if provider is None:
            raise RuntimeError('Unregistered platform secret reference')
        value = deployment_secret('ASSISTANT_CUSTOMER_' + provider.upper() + '_CLIENT_SECRET')
        if not value:
            raise RuntimeError('Platform secret is unconfigured')
        return value
    import jwt
    providers = {app.provider for app in apps}
    google_jwks = jwt.PyJWKClient('https://www.googleapis.com/oauth2/v3/certs', timeout=10) if 'google' in providers else None
    outlook_jwks = jwt.PyJWKClient('https://login.microsoftonline.com/common/discovery/v2.0/keys', timeout=10) if 'outlook' in providers else None
    tenants = [value.strip() for value in os.getenv('ASSISTANT_CUSTOMER_OUTLOOK_TENANTS', '').split(',') if value.strip()]
    identity = ProviderIdentityVerifier(http, secret, google_jwks=google_jwks,
                                       outlook_jwks=outlook_jwks, outlook_tenants=tenants)
    return {'applications': apps, 'http': http, 'platform_secret': secret, 'verify_identity': identity}
