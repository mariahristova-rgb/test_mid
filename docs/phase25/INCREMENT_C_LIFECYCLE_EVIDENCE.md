# Increment C — existing tenant-bound OAuth lifecycle hardening

14 October 2026. Local offline implementation; no general customer-account connector is activated.

Reproduced failure: an expired token refresh was interrupted by disconnect in MockTransport. The original implementation returned `late-access` and overwrote the cleared encrypted token bundle; the regression failed with “DomainError not raised”. The corrected implementation compares the current tenant-scoped connection snapshot with the original inside the existing Store transaction before accepting refresh results. A disconnect or reconfiguration wins; late token material cannot be stored or returned. Refresh failure state changes and successful encrypted token replacement use the same transaction. Remote I/O remains outside the transaction.

Changed runtime: `semantic_os/backend/assistant/google_workspace.py`. Changed tests: `semantic_os/backend/tests/test_google_concierge.py`. Existing owner restriction, exact redirect, scope validation, state expiry/replay checks, encrypted storage, booking approvals and unknown-write behavior remain intact. No public API or database schema change; current response shapes retained.

New fixtures verify interrupted refresh/disconnect, encrypted refresh-token rotation, absence of another tenant's connection, expired OAuth state without transport calls and insufficient scopes. All provider traffic uses httpx.MockTransport. This does not establish distributed locking, customer self-service, remote token revocation receipts or provider availability. Single-process Store topology remains the supported scope.

Targeted Google suite passed 25 tests after the reproduced fix; two additional tests subsequently added for rotation/expiry/scope invariants are included in the final full-suite receipt. Fresh `python -m unittest discover -s semantic_os/backend/tests`: **361/361 PASS**, 61.421 seconds. Initial sandbox run stalled before test progress and was interrupted; rerun with normal temporary-file access completed. Existing Starlette/httpx deprecation warning remains. Existing versioned corpus extended to 1.6.0 with these three cases: **51/51 PASS**, `pilot_ready=false`, tokens unmeasured with mock providers. Command: `python scripts/evaluate_phase17.py --output artifacts/phase25/offline-evaluations.json`. No live bookings, emails or customer data.

Rollback: revert only the refresh transaction correction and new tests, then rerun existing Google/booking regressions. No schema downmigration or external cleanup; reverting restores the demonstrated lifecycle defect and must not be represented as acceptance.

## Remaining Phase 25 scope

Customer OAuth connection contract, resource discovery, Microsoft/Calendly/HubSpot adapters, connector-specific entitlement categories and custom quote workflow remain unimplemented. The existing owner-pinned API is not silently widened. Catalog simulation is not a persisted connection lifecycle.

Before those changes, public API review must specify request/response shapes, tenant/role guards, capability version, scope-to-action matrix and compatibility. No real accounts, tokens, registration, billing or deployment are authorized by these local receipts. Phase 25 is not complete; public SaaS/production GO remain blocked.
