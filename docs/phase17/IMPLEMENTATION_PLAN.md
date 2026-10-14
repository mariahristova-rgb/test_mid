# Phase 17 incremental plan and approval boundaries

11 October 2026. Preserve existing Vue/FastAPI contracts, schema and both feature branches.

1. P0 local privacy fix: shared widget trace redaction and clear/retention regression tests. Files: `semantic_os/backend/assistant/widget.py`, `semantic_os/backend/tests/test_widget.py`. Run targeted tests, then existing full backend suite/source checks. Risk: erase execution payloads needed for diagnostics; retain pseudonymous status/idempotency and booking records.
2. Read-only staging inventory and synthetic browser acceptance, after scoped authorization: existing host/DNS/TLS/flags, BG/EN FAQ, mobile/focus/reconnect. No provisioning, callback/token inspection or real customer reads. Preserve stop deadline and budget.
3. Calendar/email P0: reuse `concierge.py`, `google_workspace.py`, existing uncertain-write recovery and durable jobs. Review offline lifecycle/clock failure tests first. New live actions require exact owner recipient, slot, create/reschedule/cancel/reminder types and cleanup approval. Staging OAuth connection is a separate owner interaction; do not migrate local tokens.
4. Contract/evaluation work: versioned offline corpus mapped to executable tests, negative consent/ownership/provider uncertainty/locale cases, reviewed failure promotion. Add only missing coverage, not a parallel assistant or billing ledger.
5. Website/mobile/operator work: reuse shared loader and existing views, with production deployment disabled. Produce compatibility matrix and measured baseline before optimizing. Public browser scope, device/screen-reader access and real Google acceptance remain gates.
6. Pilot packaging: per-capability checklist, rollback/disable, redacted operational receipts and explicit go/no-go. No external pilot enrollment or main merge without owner approval.

## Infrastructure spend

No new infrastructure proposed in this increment: incremental spend €0. Existing temporary Phase 16 host estimate €1.9577/week is historical pricing evidence, not current billing or a hard cap; disk/IP continue charging after the fixed stop. No deadline extension, inference VM, PostgreSQL service or extra replica is authorized. Evaluate current hosting and pricing before any later paid proposal.

Single-process SQLite is acceptable only for this isolated bounded staging topology. Multi-instance deployment requires a tested persistence adapter, durable distributed queue/locks, migration and restore evidence before replicas are enabled; it is not part of an implicit HA promise.

## Pending approvals and blockers

Scoped read-only cloud and public synthetic browser approval requested. Existing local synthetic browser authorization remains usable. Live Calendar/Gmail acceptance, production rollout, external pilot/customer data, new spending and protected-branch merge remain individually gated. The Phase 17 prompt does not waive these boundaries.
