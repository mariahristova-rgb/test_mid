# Tenant connector security verification scope

Authenticated principal supplies tenant identity. Every fixture row/secret/receipt lookup is tenant-scoped. Configure permission protects catalog/configuration/OAuth/actions/quotes; actor dependency enforces existing authentication. Cross-tenant IDs and subjects do not acquire another connection/state or token. Resource/action permissions are checked before preview.

State binding/expiry/revision prevents callback replay and disconnect revival. Token grants require scopes and identity. State-machine simulation cannot grant oauth_verified. Secrets remain encrypted; redacted projections exclude tokens. Adapter transport constructor rejects real HTTPTransport, fixed provider endpoints prevent arbitrary URL execution, and unknown writes retain receipts.

Tests verify tenant/role/revision denial, fake credential encryption, no real URLs/token input, replay protection and zero appointment/job/invoice side effects. No real customer data or existing OAuth tokens were read. This is bounded offline verification; no penetration-test certification, provider account access audit or distributed-lock claim.
