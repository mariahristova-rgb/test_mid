# Phase 5 production readiness audit

Assessment date: 2026-10-08. Scope: `test_mid` only. No destructive rewrite or original-repository access is planned.

Baseline verified before Phase 5 changes: 131 backend tests, 7 frontend tests, Vue typecheck/lint/build and source boundary scan (74 files, zero failures). Phase 4 previously also passed Windows/Linux tests, container builds, mock browser workflows and credential scans. The new application uses SQLite migrations 1–4, explicit tenant membership, RS256/JWKS authentication, two agents, approved typed tools, encrypted tenant secrets, signed communication gateways, persisted conversations and a durable messaging outbox.

| Area | Existing capability | Gap / risk |
|---|---|---|
| Channels | Shared Web Chat, voice and messaging orchestration; bilingual mock workflows; gated vendor adapters | Real LLM/calendar/payment, SMTP, Meta, Twilio and speech account tests remain absent |
| Identity | Verified subject ownership, tenant RBAC, memory-only SPA bearer tokens, demo restricted to loopback | No tenant onboarding/verification state or platform support authorization foundation |
| Billing | Operational usage records, segment/call counters | No subscription domain, hosted payment port, immutable billing usage, grace periods or central entitlements |
| Credentials | Fernet-encrypted per-tenant values | No audited retrieval, explicit revocation, versioning or managed rotation workflow |
| Database | Forward migrations and composite ownership constraints, local transaction lock | JSON payloads partly application-enforced; unpaginated queries; single-process SQLite/limiter; no tested backup/restore |
| Reliability | Transactional ingress/outbox, bounded send retries, unknown-send reconciliation, reminder versions | Worker health/error visibility and graceful draining need improvement; no billing-event idempotency |
| Privacy | Message/file/voice content retention and partial redaction | Contact/tenant export/deletion workflow and provider/backup erasure responsibilities missing |
| Deployment | Non-root containers, identity build gate, CI checks, frontend security headers | No exercised isolated staging profile, TLS edge recipe, recovery artifact or operational approval workflow |

## Implementation sequence

1. Add forward migration 5 and provider-independent onboarding, plan, subscription, invoice, payment-event and append-only usage domains. Keep prices configurable and payments mocked.
2. Enforce tenant state and backend resource/usage limits through a central entitlement service. Connect existing message/tool/voice/storage events without duplicating agent logic.
3. Add credential rotation/revocation/audit, privacy exports/deletion requests, restricted platform metadata/support grants and content-free operational metrics.
4. Reuse the Vue dashboard for bilingual onboarding, billing, usage and operations. Keep UI, conversation and voice locales independent.
5. Add bounded worker health/draining, encrypted SQLite backup and restore validation, simple staging/production container/proxy configuration and approval-gated deployment documentation/CI.
6. Run regressions, adversarial billing/security tests, required mock scenarios, measured local concurrency tests, browser verification and isolated staging/recovery tests. Record actual results and remaining blockers.

## Production blockers

Phase 5 follow-up: the SaaS domains, quota ledger/reservations, credential lifecycle, privacy/support controls, content-free operations, local TLS staging and encrypted recovery are implemented and tested. The frontend audit found three high/two moderate dependency findings; scoped upgrades and a clean peer-valid lockfile resolved them to zero. Staging revealed the WAL deserialize limitation and unprivileged gateway paths, both now covered by fixes/recovery tests. See IMPLEMENTATION_STATUS.md for final evidence; these improvements do not remove the external production gates below.

Live identity/email verification claims and provider accounts must be configured and reviewed. No real payment provider is selected or authorized. Real speech/carrier delivery and calendar/LLM quality remain unverified. Managed TLS/DNS, secret rotation, billing/tax configuration, data-processing/retention policy, provider/backup erasure, operational ownership and measured production capacity remain deployment gates. A successful local staging rehearsal will not remove those external gates or establish GDPR certification.
