# OAuth and token security

ConnectorOAuth implements provider-specific authorization previews and private authenticated completion with fake app credentials and exactly `fixture-code`. Real credentials and public callback handling are absent by design. Exact fixed loopback redirects are constructed server-side. No client redirect/base URL is accepted.

One-use state is tenant-scoped, user/subject/connection/revision-bound, browser-bound with a digest and expires after ten minutes. PKCE S256 is used for Google, Microsoft and Calendly. HubSpot fixture does not assert PKCE support without an approved provider-specific contract. Token grants require selected action scopes, access/refresh tokens and positive expiry. Provider identity must match the synthetic account; Google requires verified email and HubSpot active introspection.

Existing TenantSecretStore encrypts verifiers and fake tokens. Refresh is serialized within the local service, retains rotated material, and compares the connection before storing. Disconnect clears material and increments revision so pending completion/refresh cannot restore it. Reauthorization errors fail closed. Local state-machine connect is not OAuth-verified and cannot execute provider previews.

No token/secret goes into the UI projection, URL logs or audit payload. Authorization preview includes only a fake public client ID; UI never navigates it. Tests reject real HTTPTransport, wrong binding/tenant, expiry, replay, scope omissions and identity mismatch. Public OAuth verification, account ownership, encrypted production refresh/revocation receipts and distributed concurrency remain external gates.
