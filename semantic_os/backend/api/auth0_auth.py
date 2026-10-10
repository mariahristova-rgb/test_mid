"""Opt-in Auth0 verifier. Identity linking and deployment membership are separate gates."""
from dataclasses import dataclass
from urllib.parse import urlsplit
import logging
import os
import jwt
from fastapi import HTTPException

_logger = logging.getLogger(__name__)

# Every one of these collapses into the exact same client-facing 401
# "Invalid or expired sign-in token." -- intentionally: telling an
# unauthenticated caller *which* validation step failed (issuer, audience,
# signing key, expiry, ...) would hand an attacker a probe for this
# deployment's configuration. But collapsing them client-side must not also
# collapse them in OUR OWN logs: an issuer mismatch (a configuration
# regression -- e.g. AUTH0_DOMAIN pointing at the wrong Auth0 domain for
# where the frontend actually obtains tokens) looks nothing like an
# expired session, and only the server log can tell them apart. This maps
# each PyJWT exception type to a coarse, non-sensitive reason code; nothing
# here ever logs the token, its header, or its claims. Order matters only
# in that a more specific entry must appear before a less specific
# ancestor of the same exception (e.g. InvalidSignatureError before the
# generic DecodeError it subclasses); it does not need to match PyJWT's
# own exception hierarchy.
_JWT_REJECTION_REASONS = (
    (jwt.ExpiredSignatureError, "token_expired"),
    (jwt.ImmatureSignatureError, "token_not_yet_valid"),
    (jwt.InvalidIssuerError, "issuer_mismatch"),
    (jwt.InvalidAudienceError, "audience_mismatch"),
    (jwt.MissingRequiredClaimError, "missing_required_claim"),
    (jwt.InvalidSignatureError, "signature_invalid"),
    # Covers "no signing key found for this token's kid" -- the classic
    # symptom of a JWKS endpoint that does not serve the certificate the
    # token was actually signed with (e.g. an Auth0 custom-domain token
    # verified against the underlying tenant's default JWKS instead of the
    # custom domain's own). jwt.PyJWKClientConnectionError (a network-level
    # JWKS fetch failure, not a rejection) is handled separately below as a
    # 503, before this classification ever runs.
    (jwt.PyJWKClientError, "signing_key_not_found"),
    (jwt.DecodeError, "token_malformed"),
)


def _classify_rejection(exc: Exception) -> str:
    for exc_type, reason in _JWT_REJECTION_REASONS:
        if isinstance(exc, exc_type):
            return reason
    return "token_rejected"


@dataclass(frozen=True)
class AuthenticatedSubject:
    provider: str
    subject: str
    # Best-effort, informational only -- present only if Auth0 included
    # them in this access token's claims (not guaranteed for every
    # connection/scope configuration, and never required). Used only to
    # label a brand-new self-signup account for display (see
    # self_signup.py); NEVER used to find or resolve an existing account --
    # the verified `subject` above remains the only identity key anywhere
    # in this pipeline (see account_linking.py / test_email_never_links_an_account).
    email: str = ""
    name: str = ""
    email_verified: bool = False


class Auth0Verifier:
    def __init__(self, domain, audience, jwks=None, *, expected_issuer=None):
        issuer = 'https://' + domain.removeprefix('https://').rstrip('/') + '/'
        parsed = urlsplit(issuer)
        if not parsed.hostname or parsed.username or parsed.port or parsed.path != '/' or parsed.query or parsed.fragment or not audience:
            raise ValueError('Configure an Auth0 domain and custom API audience.')
        if audience.rstrip('/') == issuer.rstrip('/') + '/api/v2':
            raise ValueError('Use the Assistant API audience, not the Management API.')
        if expected_issuer and expected_issuer != issuer:
            raise ValueError('AUTH0_ISSUER must match the HTTPS AUTH0_DOMAIN issuer, including its trailing slash.')
        if os.getenv('ASSISTANT_ENV', '').lower() in {'production', 'prod'} and (parsed.hostname == 'auth0.com' or parsed.hostname.endswith('.auth0.com')):
            raise ValueError('Production authentication requires a custom domain.')
        self.issuer, self.audience = issuer, audience
        self.jwks = jwks or jwt.PyJWKClient(issuer + '.well-known/jwks.json', cache_keys=True, timeout=3)

    def verify(self, authorization):
        scheme, _, token = (authorization or '').partition(' ')
        if scheme.lower() != 'bearer' or not token.strip():
            raise HTTPException(401, 'Sign-in required.')
        try:
            key = self.jwks.get_signing_key_from_jwt(token).key
            claims = jwt.decode(token, key, algorithms=['RS256'], issuer=self.issuer,
                                audience=self.audience, leeway=30,
                                options={'require': ['exp', 'iat', 'sub', 'iss', 'aud']})
        except jwt.PyJWKClientConnectionError as exc:
            _logger.warning('Auth0 sign-in verification unavailable: JWKS lookup failed (%s)', type(exc).__name__)
            raise HTTPException(503, 'Sign-in verification temporarily unavailable.') from exc
        except jwt.PyJWTError as exc:
            # Client response is unchanged (still the generic 401 below) --
            # only the server log gains the specific reason, so production
            # incidents like an issuer/JWKS misconfiguration are diagnosable
            # without ever exposing that detail to the caller.
            # Reviewed: Only a fixed rejection-category enum is logged; no token or exception text.
            # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure
            _logger.warning('Auth0 token rejected: %s', _classify_rejection(exc))
            raise HTTPException(401, 'Invalid or expired sign-in token.') from exc
        if not isinstance(claims['sub'], str) or not claims['sub']:
            raise HTTPException(401, 'Invalid sign-in subject.')
        email = claims.get('email')
        name = claims.get('name') or claims.get('nickname')
        return AuthenticatedSubject('AUTH0', claims['sub'],
            email=str(email).strip() if isinstance(email, str) else '',
            name=str(name).strip() if isinstance(name, str) else '',
            email_verified=claims.get('email_verified') is True)
