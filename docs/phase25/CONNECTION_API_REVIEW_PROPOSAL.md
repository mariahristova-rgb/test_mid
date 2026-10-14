# Customer connection contract — review required

Proposed next local increment; not implemented or activated. Existing owner Google endpoints remain compatible and separate.

Review these additive paths before runtime changes:

- `GET /api/connectors`: static versioned capability descriptors; planned adapters remain COMING SOON.
- `GET /api/connectors/connections`: authenticated tenant-only redacted connection projections.
- `POST /api/connectors/connections`: configure a supported provider identifier, allowed action identifiers and resource selection; reject unknown fields/actions/providers. No arbitrary base URLs or client secrets accepted from this form.
- `POST /api/connectors/connections/{id}/test`: fixture-only readiness receipts for local execution; no provider mutation.
- `POST /api/connectors/connections/{id}/disconnect`: disable connection and invalidate pending authorization; keep unknown-write receipts unresolved. No deletion of booking/audit records.

OAuth start/callback and general Google resource discovery follow a separate provider-specific increment. Local fixtures use fake encrypted token material; no real credentials migrate. Proposed connection states: disconnected, connected, needs_reauthorization, degraded. Provider implementation availability is a separate capability field, so fake connected cannot imply live availability.

Proposed response includes `contract_version`, `id`, `provider`, `state`, `actions`, `resource_ids`, `revision`, `simulation`, redacted `failure_code`. No tokens, OAuth codes, provider response bodies, email or visitor content. Client never chooses tenant ownership. Each mutation requires configure permission and current revision; wrong tenant returns the existing safe not-found behavior. Invocation checks current state, permission, action/resource and entitlement server-side.

Persistence proposal reuses tenant-scoped operations_events and TenantSecretStore, without DDL. Do not expose internal operation-event payloads directly. Existing booking approval/idempotency and jobs remain authoritative; no second job runner or provider synchronization framework. New connector limits require separate SubscriptionPlan category review, not an implicit extension of billing.

Proposed changed files: new small `semantic_os/backend/assistant/connectors.py` contract/service; existing API wiring in `api.py`; new `test_connectors.py` using existing Store/MockTransport; existing frontend catalog, locale resources and frontend tests. No routing of existing live booking tools through this service until provider adapters pass reviewed tests.

Acceptance: tenant/role denial, stale revisions, encrypted fake credential replacement, disconnect with pending work, no blind replay after unknown writes, zero external I/O, BG/EN redacted diagnostics, old owner endpoints unchanged. Rollback removes additive routes/service and disables fixture connections; no DDL downmigration. Evidence and full authorized regression precede readiness claims.

This is a concrete public API review proposal, not a completed self-service lifecycle. Approval must explicitly cover these additive contracts before implementation under Phase 25 Section 22.
