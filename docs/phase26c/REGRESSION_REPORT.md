# Phase26C regression evidence — 15 October 2026
Baseline cbdc995a0466f78e7f89b3d16d5f964ca863926e; branch codex/phase26c-staging-acceptance, stacked on codex/phase26b-customer-oauth. Baseline PR2 exact-head CI38620840998/Gitleaks success independently verified after fetch; no merge.

| Exact command | Actual result |
|---|---|
| .venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests | Fresh baseline413 PASS/72.330s; first full implementation430 PASS/258.599s with disposable PostgreSQL enabled; final TLS follow-up431 PASS/232.193s, no skips |
| .venv/Scripts/python.exe scripts/phase26c_postgres_acceptance.py |14/14 PASS_LOCAL_RUNTIME, no skips,72.502s; includes actual PostgreSQL plus mocked providers; contention metrics in runtime report |
| .venv/Scripts/python.exe scripts/phase26c_migration_rehearsal.py | Native PostgreSQL import/dump/restore checksums, restored ledger trigger and unchanged SQLite integrity PASS,50 tables |
| .venv/Scripts/python.exe -m unittest semantic_os.backend.tests.test_postgres_store.PostgresConfigurationTests semantic_os.backend.tests.test_external_acceptance | Final strict TLS/admission safety follow-up6 PASS/0.309s |
| .venv/Scripts/python.exe scripts/evaluate_phase17.py --output artifacts/phase26c/evaluations.json | Existing corpus1.11.0,82/82 PASS_OFFLINE; pilot_ready=false |
| npm test; npm run typecheck; npm run lint; npm run build (semantic_os/frontend) | Fresh baseline and final billing-label build50 PASS, typecheck/lint/build PASS; demo fixture rebuilt separately |
| npm test; npm run build (artifacts/phase13b/ontelyx, unchanged website) |72 Vitest+6 Node PASS; typecheck/build PASS |
| .venv/Scripts/python.exe scripts/check_source.py |282 source/config files,0 failures |
| .venv/Scripts/python.exe scripts/check_migrations.py | SQLite versions1–5/integrity/FK/data preservation PASS; native PG checks separate |
| .venv/Scripts/python.exe -m pip_audit -r semantic_os/backend/requirements.lock --no-deps --disable-pip | No known vulnerabilities; warning about unhashed dependency pins retained |
| npm --prefix semantic_os/frontend audit --audit-level=moderate |0 vulnerabilities |
| artifacts/phase26c/tooling/terraform.exe -chdir=semantic_os/deploy/phase26c init -backend=false -input=false | Signed google6.50.0 installed, no backend/apply |
| Same Terraform binary: fmt, validate -json | valid=true,0 errors/0 warnings after documented fixes; lock checksums for Windows/Linux |
| .venv/Scripts/python.exe scripts/phase26c_qwen_benchmark.py | No inference; GPU NOT_MEASURED, null economics/capacity metrics |
| node semantic_os/security/scan-secrets.mjs [runtime/frontend/widget/scripts/deploy/docs paths] | Environment-secret scan308 files PASS; CI full-history Gitleaks is a separate gate |
| git -c core.whitespace=cr-at-eol diff --check | PASS |

PostgreSQL environment for actual runtime commands: PHASE26C_PG_DISPOSABLE=true and a synthetic DSN limited to127.0.0.1:55426/phase26c_fixture; credentials are disposable fixture-only. One purpose=test-mid-phase26c container,512MiB/1CPU/tmpfs, cached postgres17 image; existing cruise containers untouched. No customer database. Runtime tests are default-skipped when the explicit fixture is unavailable; skipped means BLOCKED, never runtime PASS. CI adds its own isolated PostgreSQL service with the same narrow fixture identity.

Initial failures: Docker daemon unavailable; started installed Docker Desktop and reran actual PostgreSQL checks. Terraform initial compact HCL formatting failed, corrected; vendor schema rejected obsolete require_ssl, replaced by ssl_mode ENCRYPTED_ONLY and valid0 errors. Browser exposed wrong conversation-only invoice placeholder; localized billing-only replacement verified in rebuilt BG UI. Manual reader failure remains unresolved, not relabelled PASS. Starlette/httpx deprecation warning remains. No failure assertions removed.

Fresh browser in Phase26C Synthetic Workspace: empty organization field→Continue exposes localized error and focuses invalid INPUT with aria-describedby=setup-error; correction/save retains input and revision1. Six required BG/EN scenarios PASS in Test Studio. 320/390 widths document305/375 respectively,zero clipped visible form controls. BG persists to Billing. Mock accounting clearly labelled; no payout system, checkout/refund or invoice mutation performed. Final invoice placeholder visibly correct; screenshot artifacts/phase26c/billing-bg.png. Real reader/audio and200% text zoom remain BLOCKED; full register/import/real-connect/publish/usage journey NOT_TESTED.

No real OAuth/provider mutation, customer messages, payment, model execution, cloud deployment, DNS, customer data or protected merge. New cloud spend0. Exact final commit/CI link is recorded in the draft PR; green CI cannot promote external acceptance.

Implementation commits: e56734b (Store/migration),914f59e (gates/IaC/inference),ca113d7 (billing). Final documentation commit records this exact tested source tree. CI additionally runs real disposable PostgreSQL and vendor Terraform validation; final exact-SHA result is attached to the draft PR.
