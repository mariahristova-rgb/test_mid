# Reviewed connection API — implementation evidence

Historical Increment C receipt. Provider protocol fixtures, UI and entitlements were subsequently added under explicit user instruction; see PHASE25_FINAL_EVIDENCE_MATRIX.md. Earlier counts and missing-capability statements below describe that earlier checkpoint.

Local fixture-only service, 14 October 2026. Implements reviewed catalog/list/create/test/disconnect routes in `connectors.py`, registered by existing `api.py`. Explicit `create_app(connector_fixtures=True)` is required along with demo mode and a non-strict environment. Default, staging and production service calls fail closed. No env switch silently enables it.

Contract: provider enum, action allowlist and synthetic resource IDs (`fixture-*`). Unknown fields, real URLs and token inputs are rejected. Create is idempotent by tenant-scoped canonical provider/action/resource configuration. Mutation requires current revision; stale/replayed mutations fail. Responses project only reviewed fields, plus locale/result/retry indication on test. Planned provider availability remains COMING_SOON even when a fixture state reads connected.

Persistence reuses operations_events and encrypted TenantSecretStore. Secret values are server-generated fake material only. State transitions include connected, disconnected, needs_reauthorization and degraded. A simulated unknown outcome cannot be cleared by reconnect/test; disconnect clears fake credentials while retaining uncertainty. No booking/job/provider-write path is attached to this service. It does not cancel real pending jobs or provide real OAuth, calendar discovery, CRM mapping, webhook handling or reconciliation.

Authorization uses configure permission, tenant-scoped lookup and existing PlanEntitlementService.access. This enforces current subscription access, not connector-count or provider-tier limits; those categories remain a separately reviewed entitlement increment. No SaaS plan price/limit or billing activation change.

Fresh evidence: five test methods cover all four providers in both locales, fixture lifecycle, encryption, zero external I/O, no appointment/job/invoice creation, cross-tenant/role refusal, stale revisions, unknown preservation, input rejection, default disable, create replay and existing Google API compatibility. Initial full suite before the final create-replay case passed 365 tests. Versioned corpus 1.7.0 passes 55/55; initial corpus attempt rejected the unreviewed module, then the explicit test_connectors allowlist addition passed. No validation weakening or parallel evaluation framework.

Frontend suite remains 40/40 PASS. Final full backend regression: **366/366 PASS**, 48.243 seconds, using `python -m unittest discover -s semantic_os/backend/tests`. Whitespace check PASS. Actual operator UI for persisted fixture connections is not yet implemented; prior browser catalog results apply to the display-only example.

Files: `semantic_os/backend/assistant/connectors.py`, `semantic_os/backend/assistant/api.py`, `semantic_os/backend/tests/test_connectors.py`, `semantic_os/config/phase17_evaluations.json`, `scripts/evaluate_phase17.py`. No DDL, existing route deletion, real OAuth tokens, live emails, appointments, paid inference, telephony, public deployment or protected merge.

Rollback removes the route registration/service and disables fixtures; fixture operations_events may remain inert and tenant-scoped. Do not delete booking records, jobs or uncertainty receipts. Rerun existing Google/API/UX and corpus tests. The old owner Google integration remains unchanged except the separately documented refresh/disconnect correction.

Phase 25 remains incomplete: customer OAuth/resource/action configuration, provider-specific adapters and negative tests, webhook/CRM mappings, connector entitlement limits, custom quote operator workflow and final 20-scenario acceptance package still require implementation and reviewed contracts. No public SaaS GO.
