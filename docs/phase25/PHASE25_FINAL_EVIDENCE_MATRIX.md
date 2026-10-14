# Phase 25 — current bounded delivery evidence

14 October 2026. **Requested local provider/OAuth/entitlement/quote implementation delivered within the described fixture scope. Full Phase 25 and public SaaS readiness are NOT established.** No real account activation, billing, deployment or push.

| Work | Evidence / limit |
|---|---|
| Provider-specific adapters | Google/Graph calendar codecs; Calendly reads; HubSpot narrow contacts; MockTransport only |
| Customer-shaped OAuth | Four provider profiles, scope/identity/state/PKCE/refresh fixtures; fixed synthetic identity and credentials; no public consent integration |
| Entitlements | Optional existing plan fields; server caps/provider gates; no commercial package activation |
| Quote workflow | Tenant-scoped idempotent scoping requests, €99/€199 separate maintenance, enterprise custom; human review pending |
| UI | Existing Google admin view, BG/EN synthetic workspace, explicit consent/results; default service disabled |
| Backend | **375/375 PASS**, 51.204s, after restore/wrong-resource/entitlement downgrade regressions |
| Evaluation | Corpus 1.8.0: 64/64 PASS, pilot_ready=false, token usage unmeasured mock providers |
| Frontend | 40/40 tests, typecheck/lint/build PASS; environment-secret build scans PASS |
| Website | Unchanged source; 72 Vitest + 6 Node tests PASS, build/typecheck/config/format PASS |
| Source/schema | 252 files zero source failures; schema 1–5, integrity/FKs/data preservation PASS |
| Secret/diff scans | Environment-secret scan 234 files PASS; diff whitespace PASS |
| Browser | Four connected fixtures, bilingual previews and scoping; 320px bounded geometry and sampled keyboard PASS |

Failures recorded: synthetic contact-read initially 404 because fixture did not seed a selected resource; fixed fixture and targeted suite PASS. Website sandbox ENOENT caused four zero-test suites; rerun with normal temporary access passed. Attempted wrong script `check:format` did not exist; actual `format:check` passed. No suppressed failures or invented benchmarks.

## Exact source/test changes for this delivery

- backend/assistant: `connectors.py`, `connector_adapters.py`, `connector_oauth.py`, `connector_fixtures.py`, `api.py`, `entitlements.py`, `saas_domain.py`.
- backend/tests: `test_connectors.py`.
- frontend: `components/ConnectorWorkspace.vue`, `components/ConnectorCatalog.vue`, `views/GoogleWorkspaceView.vue`, both locale JSON resources, `tests/connector-catalog.test.mjs`.
- corpus/runner: `semantic_os/config/phase17_evaluations.json`, `scripts/evaluate_phase17.py`.
- Earlier uncommitted Phase 25 lifecycle fix: `google_workspace.py`, `test_google_concierge.py`; separately evidenced.
- Documentation: docs/phase25, including required design/security/provider/pricing/acceptance reports. Ignored browser fixture/build/screenshots are synthetic evidence, not production artifacts.

## Compatibility and rollback

Additive local endpoints; existing routes/owner pin/booking approval and uncertainty semantics retained. No DDL. Optional SubscriptionPlan fields preserve old snapshot behavior. Fixture-only APIs return unavailable unless explicitly enabled in a non-strict demo composition root. No client secrets, real callback or live HTTP configuration is provided.

Disable first by omitting connector_fixtures or stopping the named loopback fixture. Revert this delivery's reviewed diff on the feature branch, rebuild frontend, rerun Google/UX/SaaS/corpus/schema checks. Leave fixture records inert rather than delete audit/unknown receipts. No external event, email, payment or migration cleanup needed. No protected merge or push.

## Open gates / NO-GO

Real customer OAuth consent and verified account/resource ownership; public registration/verification; provider plan/role claims; remote revocation; persistent live tool/booking integration; full Calendly scheduling/cancellation/reschedule and real webhook mapping; Outlook shared/personal strategy; HubSpot associations/notes and concurrent remote duplicate reconciliation; human commercial approvals; full accessibility review and controlled external acceptance. Single-process SQLite has no high-availability claim. No new spending or infrastructure.

## Executed regression commands

Final safety follow-up: 16/16 connector tests PASS (1.117s), including OAuth disconnect during token exchange and default-disabled API returning 503. Runtime unchanged since the 375-test full-suite run; these two additional targeted tests are not represented as a fresh 377-test full run. Initial test edit misplaced the existing mismatch block and caused a NameError; corrected placement and rerun passed. No live action or secret access.

Backend: `.venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests`; full final output in ignored `artifacts/phase25/backend-final.log`. Evaluation: `.venv/Scripts/python.exe scripts/evaluate_phase17.py --output artifacts/phase25/offline-evaluations.json`. Source/schema: existing `scripts/check_source.py` and `scripts/check_migrations.py`. Frontend: `npm test`, `npm run typecheck`, `npm run lint`, `npm run build`. Website: `npm test`, `npm run build`, `npm run typecheck`, `npm run format:check`, `npm run test:config`. Existing deprecation warning retained; no dependency changes.
