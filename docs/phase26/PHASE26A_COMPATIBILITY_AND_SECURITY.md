# Compatibility and security
Merged 382-test suite includes tenant/RBAC, consent, booking idempotency, uncertain outcomes, connector fixture lifecycle, production connector contract validation and mock payment isolation. Existing routes, draft steps 0–6 and schema migration versions 1–5 remain compatible. FAQ indexing remains ephemeral exact-match approved content with locale/hash provenance; no embeddings or paid model calls.

Connector fixtures remain disabled in strict staging/production. Production app contracts remain validation-only and do not activate customer OAuth. Owner Google compatibility remains separate. No secrets, real account tokens, customer databases or provider endpoints were accessed. No email, booking, billing, telephony, infrastructure or deployment action occurred.

Limits: environment-secret scans do not replace Gitleaks; a passing single-process SQLite suite is not multi-instance or PostgreSQL evidence. Remote CI/security advisory checks and human accessibility acceptance remain gates.

Rollback before main integration: leave main at its baseline and select the recorded safety branch in an isolated checkout. After any future authorized merge, use a reviewed revert of that merge (first parent main), never shared-history reset. No data migration was added by reconciliation.

