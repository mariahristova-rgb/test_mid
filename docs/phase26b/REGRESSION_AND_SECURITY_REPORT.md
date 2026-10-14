# Increment A regression evidence — 2026-10-14
Branch: codex/phase26b-customer-oauth. Scope is local OAuth foundation, not full Phase26B.

- Initial new-module regression failed with missing module, then implementation added.
- Connector plan-limit regression initially failed (second customer connection was allowed). Shared entitlements now count both customer_connection and connector_fixture. Removed shadowed duplicate method without changing the surviving policy.
- .venv/Scripts/python.exe -m unittest semantic_os.backend.tests.test_customer_oauth -v: 12 PASS, including public HTTPS callback/cookie/replay, signed identity, cross-tenant/expiry/binding, absent configuration, two-Store refresh claim, disconnect and scope downgrade, discovery/selection and entitlements.
- .venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests: 394 PASS, 53.842 seconds. Earlier intermediate 392 PASS is superseded.
- .venv/Scripts/python.exe scripts/evaluate_phase17.py --output artifacts/phase26b-evaluations.json: 69/69 OFFLINE_CONTRACT_ONLY, pilot_ready=false; existing corpus version1.9.0, no parallel framework.
- Source checks and migration/environment-secret checks are run separately; detailed console receipts are retained in ignored artifacts. Full-history Gitleaks CI will run on the pushed feature checkpoint; no local Gitleaks result invented.
- Frontend/website source unchanged in Increment A. Verified Phase26A frontend46 tests/typecheck/lint/build and website72+6 remain prior receipts, not newly run here.

Sandbox ASGI test stalled; authorized offline retry passed. Starlette/httpx deprecation warning persists. No provider credentials read, account activated, email/event/card sent, customer data accessed, main merged or cloud resource created. Docker read-only audit found Docker Desktop Linux daemon unavailable; PostgreSQL/container rehearsal was not run.

Changed runtime files: backend/assistant/customer_oauth.py (new), api.py (optional server injection/additive routes), connector_contracts.py (additive lifecycle states), entitlements.py (shared limits). Test file: backend/tests/test_customer_oauth.py. Existing evaluation runner allowlist and corpus extended. Documentation under docs/phase26b is an honest partial readiness package.

Rollback: omit customer_oauth_options to keep authorization disabled; revert Increment A commits on the feature branch. No DDL migration or real token migration. Legacy owner OAuth and fixture routes preserved. Full Phase26B/pilot/public production are NO-GO pending remaining implementations and external evidence.
