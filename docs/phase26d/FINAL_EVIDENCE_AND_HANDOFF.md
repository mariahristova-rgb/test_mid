> Safe acceptance update: PostgreSQL usage-history HTTP500/SQLSTATE42803 and worker ownership GET under global lock are now independently reproduced. The older local test counts remain historical PASS_LOCAL_ONLY; no current complete-suite PASS. See ../phase26e/END_TO_END_ACCEPTANCE.md.

# Phase26D evidence and Phase26E Gate 0 handoff

Date: 26 October 2026 (Europe/Sofia). Baseline: 849d602aefdde6945fcbd3af51ab4711507dc9e5. Dedicated branch codex/phase26d-reliability-gates; [Draft PR #4](https://github.com/mariahristova-rgb/test_mid/pull/4), base Phase26C. PR1/2/3 remain unmerged, main unchanged. Remote-at-entry c9c38cd lacked runtime fixes because they were local work in progress, subsequently committed as 5ebe2585399a25934be679a71179281d3c4c32cb. Certifi audit correction is separate commit 88639af439e4244131bd8c0435aa3df84aec7698. No stashes, resets, force pushes or lost changes. Final evidence-only commit carries the same tested runtime source; its SHA is returned in the delivery/PR.

## Reproduced defects and minimal changes
- customer_booking.py final pre-write admission (lines 269–287): actual disconnect after availability previously still sent POST. Recheck current committed claim, connection/resource revision, consent/tool/assistant/channel before admission. Writes admitted before disconnect may complete; truthful receipt or uncertainty remains. The create POST is outside the global transaction, but later acceptance exposed ownership GET under that lock (LOCK-SCOPE-02); reconciliation never recreates.
- postgres_store.py operational error boundaries (Database._execute, PostgresStore.connection/transaction): actual statement timeout leaked QueryCanceled. Controlled provider_error/503, rollback and pool/lock release now verified, including killed backend and bounded exhaustion. Global advisory lock unchanged.
- Existing Python lock pins: certifi 2026.7.22 -> 2026.10.19 for PYSEC-2026-4320; no certificate validation bypass. Speech environments/models not started.
- Existing fault test module/worker/recorder expanded; independent native dump restore helper and three offline Terraform mock-plan controls added. CI adds independent restore PostgreSQL service and executes plan tests. No API/schema/framework/provider feature change.

Exact changed files are the PR diff. Runtime source files: semantic_os/backend/assistant/customer_booking.py, semantic_os/backend/assistant/postgres_store.py; lockfiles requirements.lock/requirements-stt.lock/requirements-neural-tts.lock; scripts/phase26d_fault_worker.py; semantic_os/backend/tests/test_phase26d_faults.py; tests/support/fault_recorder.py and restore_oracle.py; semantic_os/deploy/phase26c/tests/phase26d.tftest.hcl; .github/workflows/ci.yml; evidence under docs/phase26d and the blocked entry record under docs/phase26e. Temporary browser support lives only in ignored artifacts, not shipped runtime.

## Executed regression
| Command / directory | Observation |
|---|---|
| `.venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests -v`, fixture env in POSTGRES_FAILURE_AND_RESTORE.md | Final runtime SHA 88639af439e4244131bd8c0435aa3df84aec7698: 445 PASS, zero skipped, 503.011s. Includes 12 native PostgreSQL booking/store and 14 process/DB/restore faults; other tests retain their existing offline stores. Not 445 PostgreSQL routes. Independent raw log hash/timestamp/command in REGRESSION_RECEIPT.json. |
| Targeted process fault module | Earlier 14 PASS / 265.891s; repeated within final full suite. Two original pre-fix failures retained in BEFORE_AFTER_RECEIPT.json and ignored raw trace. |
| `scripts/evaluate_phase17.py --output artifacts/phase26d/evaluations-final.json` | Existing corpus 82/82 PASS_OFFLINE, pilot_ready=false; safety assertions/corpus unchanged. |
| `npm test`, `npm run typecheck`, `npm run lint`, `npm run build` in semantic_os/frontend | 50 PASS / zero skips, typecheck/lint/build pass. Frontend source unchanged from 5ebe258; final backend lock patch does not alter it. Production-default build first; temporary mock-login fixture build separately. |
| `npm test`, `npm run build` in unchanged artifacts/phase13b/ontelyx | 72 Vitest + 6 Node PASS, typecheck/build pass. First sandbox attempt failed on temporary-file ENOENT, preserved in tool output; unchanged rerun outside restricted temp environment passes. No website edits/push. |
| `scripts/check_source.py` | 286 source/config files; zero failures. |
| `scripts/check_migrations.py --output artifacts/phase26d/migrations-final.json` | SQLite versions 1–5/FK/integrity/preservation pass; native PostgreSQL restore separately verified. BackupManager remains SQLite-only and rejects PostgreSQL. |
| `python -m pip_audit -r semantic_os/backend/requirements.lock --no-deps --disable-pip` | First FAIL certifi advisory; minimal pin correction and repeat no known vulnerabilities. Existing incomplete package hashes remain a limitation. |
| `npm --prefix semantic_os/frontend audit --audit-level=moderate` | Zero vulnerabilities. |
| Terraform 1.14.9 `fmt -check -recursive`, `init -backend=false -input=false`, `validate`, `test -no-color` in semantic_os/deploy/phase26c | Vendor Google 6.50.0 valid; 3 mock plan tests pass. First sandbox DNS/plugin attempt failed; supported rerun passes. Never apply. POLICY_RECEIPT.json. |
| Gitleaks 8.24.3 `detect --redact --log-opts="--all --full-history"` | Local history scanned, no leaks. Docs separately scanned. Final post-evidence-commit scan required before push; no allowlist broadened. |
| `git -c core.whitespace=cr-at-eol diff --check` | Pass. |

## Independent local observations
SQL rollback/status/counts and catalog checks are independent of application responses. Recorder is a separate HTTP server with its own durable SQLite provider DB; all actual provider traffic is loopback. OS subprocess exits 90/91/92 and two recovering processes are actual termination/restart evidence. PostgreSQL server logs independently show timeout, administrator backend termination and deadlock. No real Google endpoint was called.

Final restore: PostgreSQL 17.11, dump 0.958s, restore plus SQL/catalog/hash validation 2.648s; 250042 bytes, 480 TOC entries. Dump SHA256 8100422d99aed593ef36617f21f9205bf74eafb6ffcbc83b6fbd2455b3052921. Both tenant datasets, complete table hashes/catalog definitions and append-only ledger preserved. Zero acknowledged snapshot records lost is this snapshot drill only; not a production RPO. Timing excludes operator/app recovery; not production RTO. Binary dumps stay ignored locally. Independent restore retains an uncertain source intent and GET-only recovery produces one event without POST replay.

Negative controls: deliberate duplicate POST count and wrong-tenant projection rejected; altered restored jobs hash rejected; raw restored ledger DELETE rejected. Original consent-race and raw-timeout assertions fail before fix and pass after. Not every proposed invariant has a separate mutation test; no blanket assertion of all planned controls passing. Same/cross-tenant synthetic throughput in LOCAL_RUNTIME_RECEIPTS.json is only two-process/20-operation observation; consistency lock serializes writers, no production capacity ceiling or tenant-per-GPU inference.

## Blocked gates and adversarial review
Authoritative GitHub check 121612762049 at c9c38cd: job never started because recent account payments failed or spending limit needs increase. BLOCKED_EXTERNAL_INFRA, not CODE_FAILURE or PASS_CI. Exact-head successful CI remains mandatory; no billing setting or branch protection changed. REMOTE_GATE_RECEIPT.json preserves source metadata. Pushing the evidence is not CI completion.

Historical screen-reader FAIL (nothing spoken) remains BLOCKED_HUMAN, with no named reader/browser receipt. Full observed signup/FAQ/preview/widget/usage/disconnect journey remains incomplete; SELF_SERVICE_ACCESSIBILITY.md records precisely the bounded browser work and support intervention. Whole-app PostgreSQL API parity, cloud backup API, distributed quotas and cloud kill drill are not certified by this suite. Provider consent/resource/create/cleanup, IAM/routing/cloud cost/GPU telemetry and independently reviewed cloud approval remain absent. No participant enrollment, primary-calendar access, customer data, external email, payment or paid model run occurred.

Codex adversarial source review checked pre/post-admission revocation, stable event identity, worker claim comparison, uncertainty projection, rollback and tenant scoping. This is self-review, not independent human engineer approval. Human review checklist is in STAGING_SECURITY_COST_AND_KILL.md. No unsupported provider paths were enabled.

## Decision / handoff
- Executed local process/PostgreSQL experiments: PASS_LOCAL_ONLY.
- Phase26D closure / Phase26E Gate 0: NO_GO / BLOCKED_EXTERNAL_INFRA; do not begin new Phase26E implementation or manufacture pass receipts.
- Limited private staging: NO_GO, missing approval/cloud-runtime/backup/kill evidence.
- External 3–5 business pilot: NO_GO, missing isolated provider and human/journey acceptance.
- Public production: NO_GO / out of scope.

Owner next action: resolve GitHub Actions account eligibility without an automatic spend-limit change; then run exact-head CI and independent review. Engineer next local gate: complete the documented end-user journey, with genuine named human screen-reader observation when available. Provider/cloud actions require separately scoped fresh approvals; not requested or inferred here.

Safe rollback: disable admissions and quiesce writers first; preserve pending/uncertain jobs, external IDs, audit and ledger. Revert application commits on a review branch only; no schema downgrade, no blind POST retry, no automatic switch to stale SQLite. Native restore goes to a new owned database and is verified before any separately approved cutover. Only owned disposable containers are removed after fixture cleanup; ignored synthetic dump/receipts retained. Main and unrelated runtime containers remain untouched.
