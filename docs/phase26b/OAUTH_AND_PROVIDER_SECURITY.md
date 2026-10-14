# Increment A security evidence
Implemented customer_oauth.py uses existing PlatformOAuthApplication/CustomerConnectionConfig, operations_events, TenantSecretStore and provider profiles. New customer paths are separate from owner-bound /api/google and fixture /api/connectors contracts.

State binds tenant, subject, user ID, provider, connection revision, app-config hash, expiry and browser-binding hash. PKCE is applied for providers declaring support. One-use state is consumed before exchange; reconnect obtains new state after failed exchange. Verified Google JWT requires RS256 signature, allowed issuer, exact audience, exp/iat/sub/nonce and verified email claim. Customer subject is independent of the legacy owner allowlist. No customer-entered client secrets.

Public callback recovers tenant/member only from opaque state and rechecks configure rights. Secure HttpOnly SameSite=Lax cookie is restricted to the exact provider callback path. Response excludes credentials/account PII and uses no-store/no-referrer. OAuth request URLs must be excluded from deployment access logs; staging logging acceptance remains open.

Refresh claim persists before I/O, denying a concurrent refresh across two SQLite Store instances. Disconnect/revision change wins over late exchange/refresh. Failed/unknown refresh requires reauthorization; a crashed claim requires disconnect/reconnect rather than blind retry. No process-only lock is used as sole protection. This proves bounded SQLite behavior, not distributed PostgreSQL readiness.

Scope downgrade, forged identity, cross-tenant callbacks, binding mismatch, expiry, callback replay, absent server configuration, disconnect races and shared connector limits tested with mock HTTP. Accounts/tokens encrypted; readback projections are redacted. Live transport/configuration is not enabled by default. Unsupported identity verifiers fail closed.

Remaining: production transport/credential loading, reviewed provider-specific identities beyond Google, provider revocation receipt, app rotation acceptance, privacy/retention approval, actual customer UI and live accounts. No LIVE_VERIFIED claim.
