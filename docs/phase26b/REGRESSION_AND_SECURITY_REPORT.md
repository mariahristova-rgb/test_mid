# Follow-up regression evidence — 2026-10-14
Branch codex/phase26b-customer-oauth; baseline 8ffcba7. Local mock contracts and data-portability evidence; no live acceptance.

| Exact command / working directory | Result |
|---|---|
| .venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests | Final: 413 PASS, 137.957 seconds (prior 412 PASS, 170.754 seconds superseded) |
| .venv/Scripts/python.exe -m unittest semantic_os.backend.tests.test_customer_booking semantic_os.backend.tests.test_customer_oauth semantic_os.backend.tests.test_provider_identity | Final policy/guard follow-up: 30 PASS, 6.008 seconds |
| .venv/Scripts/python.exe scripts/evaluate_phase17.py --output artifacts/phase26b-evaluations.json | 79/79 PASS; existing corpus 1.10.0; OFFLINE_CONTRACT_ONLY, pilot_ready=false |
| npm test (semantic_os/frontend) | 50 PASS |
| npm run typecheck; npm run lint; npm run build (semantic_os/frontend) | PASS; zero lint warnings; source/dist secret scan PASS |
| npm test (artifacts/phase13b/ontelyx unchanged website checkout) | Authorized retry: 72 Vitest + 6 Node PASS |
| npm run build (same website) | Typecheck/build PASS |
| .venv/Scripts/python.exe scripts/check_source.py | 275 files, 0 failures |
| .venv/Scripts/python.exe scripts/check_migrations.py | Versions 1–5; FK/integrity/data-preservation PASS |
| .venv/Scripts/python.exe scripts/check_phase26b_staging_plan.py | Static admission PASS; vendor schema validation NOT_EXECUTED |
| .venv/Scripts/python.exe scripts/phase26b_postgres_rehearsal.py --container test-mid-phase26b-pg-rehearsal-20261014 --output artifacts/phase26b-postgres.json | Import/dump/restore/SQLite rollback PASS; 83 FKs, all-table checksums; two tenants including appointments/jobs/messages |
| node semantic_os/security/scan-secrets.mjs semantic_os/backend/assistant semantic_os/frontend/src semantic_os/widget scripts docs/phase26b | 290 files PASS |
| git -c core.whitespace=cr-at-eol diff --check | PASS |

## Reproductions and initial failures
- DST slot search initially raised timezone_required on ambiguous Sofia 03:00. Now skips ambiguous/nonexistent wall times while preserving valid slots; targeted test PASS. Real provider/business refusal rules are preserved.
- Bridge fixture initially replaced tenant policy instead of merging it and lost entitlement fields (KeyError); corrected fixture merge. Initial callback redirect return typo corrected; targeted test PASS.
- Website sandbox test failed on missing temporary transform files (43 tests passed, three suites failed). Same offline test under authorized host runtime passed 72+6; no website source change.
- Commands issued from the wrong root initially produced npm ENOENT/ESLint file-not-found; corrected working directory and full checks passed.
- Disposable-container reset guard initially treated empty PowerShell object as nonempty; reset refused safely. Exact label/network/empty-port check then passed before reset. No other container touched.
- Starlette/httpx deprecation warning persists; no passing tests were skipped.

## Browser-observed evidence
Named disposable Phase26B Synthetic Workspace, loopback 8020, mock transport only. Sign-in, calendar discovery, selection/save, explicit booking consent/activation passed. Final build displays enabled state after reload/re-login. BG/EN resource and consent labels observed. At 320/390/768/1280 widths the document scroll widths were 305/375/753/1265, with no horizontal overflow; provider buttons were at least 44px high (65px at BG 320). Keyboard Tab from resource chooser reached the labelled disconnect checkbox with visible focus. Screenshots were visually inspected. Provider OAuth authorization was not clicked; no external accounts involved.

Manual reader result remains FAIL/unverified; real 200% text zoom and full customer register/import/publish/usage journey remain open. Billing visual acceptance is not newly certified by this connector increment.

## Compatibility, limits and rollback
Additive API projections/routes and existing Store schema; legacy owner/fixture paths, agents and frontend contracts preserved. New worker uses existing durable jobs and bounded claims; unknown provider writes reconcile by GET only. Customer cancellation/rescheduling and non-Google agent writes fail closed. PostgreSQL runtime/distributed claims and vendor deployment are not implemented by data import tests. Async confirmed business analytics currently undercounts rather than inventing completed outcomes.

Default disable: ASSISTANT_CUSTOMER_OAUTH_ENABLED unset/false and ASSISTANT_CUSTOMER_CALENDAR_WRITES_APPROVED unset/false. Retain uncertain jobs/audit records; do not replay writes. Revert feature commits on the isolated branch; no DDL or real-token migration. No paid model, provider event/email, customer data access, main merge or cloud resource. Full Phase26B, limited external staging and public production remain NO-GO. Full-history Gitleaks/CI results must be associated with the pushed exact SHA; local environment scan is not a substitute.

Final widget projection follow-up: .venv/Scripts/python.exe -m unittest semantic_os.backend.tests.test_widget semantic_os.backend.tests.test_customer_booking — 29 PASS, 18.453 seconds. Calendar state now comes from the provider outcome rather than a fixed mock label. Implementation commits: 86f152a (provider/bridge), 5a8b98f (UI/widget), 19e4441 (persistence/staging checks).
