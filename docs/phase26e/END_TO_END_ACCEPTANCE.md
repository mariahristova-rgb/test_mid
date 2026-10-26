# Safe acceptance continuation - 26 October 2026

Authorization: independently verifiable local acceptance only, while GitHub CI is blocked. Existing branch `codex/phase26d-reliability-gates`; no Phase26E implementation branch, runtime code changes, provider contact, paid resources or main merge. Entry fetch confirmed clean local/remote c71b06a2a93352cf5353b704531d2dd1b6b77eb9 and Draft/unmerged PR4.

## Decision: NO-GO, with newly reproduced defects

| Claim | Result | Independent evidence |
|---|---|---|
| Preserved 445 backend / 14 fault tests | PASS_LOCAL_ONLY, historical | Raw backend log SHA256 matches REGRESSION_RECEIPT; retained binary restore dump hash matches its receipt; production booking/store modules unchanged |
| Fresh booking/OAuth/native PostgreSQL regressions | PASS_LOCAL_ONLY | 40 tests, zero skips, 103.972s; includes 12 actual PostgreSQL booking/store cases. Raw output hash in SAFE_ACCEPTANCE_RECEIPTS.json |
| BG/EN registration, mock verification/trial, approved inline FAQ, save/resume, preview | PASS_LOCAL_ONLY per step | Actual FastAPI routes via TestClient, native PostgreSQL and 8 isolated preview cases per language; not a browser customer study or indexed knowledge import |
| Mock consent-controlled booking, duplicate prevention and ledger consistency | PASS_LOCAL_ONLY per step | Two synthetic tenants, one confirmed SQL row and 12 ledger rows each, independent recorder observes exactly one create POST/event each; duplicate confirmation leaves ledger unchanged |
| Provider authorization negative controls | PASS_LOCAL_ONLY | Wrong-tenant identity 401, absent explicit configuration confirmation 403, wrong domain nonce 409, stale disconnect revision 409. Current revision disconnect denies subsequent writes |
| Synthetic domain proof/widget publication | PASS_LOCAL_ONLY per step | Actual loopback HTTP nonce file with text/plain, existing verify/publish routes; fake OAuth exchange/identity and nonce installation are declared support interventions, not real consent. Browser widget installation is NOT_TESTED |
| Usage summary and billing | PASS_LOCAL_ONLY per step | Existing routes return successfully; browser Bulgarian labels and mock-only notice observed |
| Complete journey including usage history | FAIL | Both BG/EN tenants receive HTTP500 at /api/workspace/usage?period=2026-10; direct independent SQL returns SQLSTATE42803 |
| Worker HTTP entirely outside global transaction | FAIL | Independent pg_locks query sees ownership/read GET while advisory lock26260001 is granted; create POST itself is outside the transaction |
| Browser keyboard setup/resume/6 required previews | PASS_LOCAL_ONLY, bounded observations | EN/BG invalid-input errors rendered, invalid input focused, correction progresses; revision3 resumes after Billing/Usage navigation; six required mock BG/EN previews PASS |
| Mobile DOM geometry | PASS_LOCAL_ONLY, limited | Width320/document305 and width390/document375; zero horizontally clipped visible form controls. Screenshot in ignored artifacts/phase26e/setup-bg-320.png. Not blanket accessibility/visual acceptance |
| Spoken screen-reader output | BLOCKED_HUMAN | Historical user FAIL remains; no named reader/browser/version or genuine spoken transcript. DOM/focus is not human evidence |
| Complete browser signup-to-disconnect; actual200% text zoom | NOT_TESTED | API execution cannot substitute for these steps |
| Exact-head CI | BLOCKED_EXTERNAL_INFRA | Check121652650621 at c71b06a: GitHub job never started due account payments/spending restriction |
| Real provider/cloud/pilot | BLOCKED_APPROVAL | No real OAuth, calendar mutation, email, customer enrollment, GPU, cloud resource or spend |

## Defects, not evidence inflation

**PG-USAGE-01:** `CustomerWorkspace.usage` groups JSON projections by names including `assistant_id`, which also exists as an input table column. PostgreSQL resolves GROUP BY to the input column, leaving the selected JSON expression ungrouped: `GroupingError`, SQLSTATE42803. Browser shows the localized provider error; actual HTTP response is500. `strftime` is present in the query, but the PostgreSQL bootstrap already defines a compatibility function: missing strftime is NOT the reproduced cause. The strict new acceptance test requires200 for both tenants and remains red. Do not replace this route with the working `/api/usage` summary.

**LOCK-SCOPE-02:** final write admission calls `context`, which performs `service.resources` HTTP while the transaction/global advisory lock is held. The create POST remains outside. Earlier Phase26D statements claiming no HTTP at all under that lock were too broad and are corrected here. A separate connection queried pg_locks for the actual worker backend PID during mock transport execution. This is a lock-scope/reliability finding, not evidence of duplicate bookings or tenant leakage. The regression rejects HTTP under this lock as required by the handoff. No production correction was made under this acceptance-only authorization.

Strict test at 36f3dd4f6b8862bd25c331ff63fa5f2ead9280bd: 1 FAIL /47.367s, no skips. Both complete API attempts reach final disconnect and collect receipts before the four strict failures (two locales x usage/lock scope) are asserted. Fresh40-test regression is independent of this failing test. There is no fresh full446-test PASS claim; the old445 PASS cannot certify the expanded suite.

## Harness corrections retained transparently

Initial harness attempts incorrectly expected conversation creation200 instead of existing201, omitted explicit widget origin/loopback allowance and nonce Content-Type, used a stale revision for disconnect and expected wrong-tenant404 rather than the earlier identity401. These were harness contract/configuration mistakes, corrected without changing runtime or removing the positive security assertions. The broader initially passing route sequence did not include usage history; adding the actual browser-used endpoint exposed PG-USAGE-01. New negative controls retain strict authorization, nonce and ledger checks. The final test is deliberately not skipped or expected-failure-labelled.

## Reproduce / limits

Use the same two bounded, labelled, loopback-only disposable PostgreSQL fixtures described in docs/phase26d/POSTGRES_FAILURE_AND_RESTORE.md. Set PHASE26C_PG_DISPOSABLE=true, PHASE26D_PG_DISPOSABLE=true and the reviewed source DSN, then run:

```powershell
.venv/Scripts/python.exe -m unittest semantic_os.backend.tests.test_phase26e_acceptance -v
.venv/Scripts/python.exe -m unittest semantic_os.backend.tests.test_postgres_store semantic_os.backend.tests.test_customer_oauth semantic_os.backend.tests.test_customer_booking -v
```

First command is expected to fail until both reproduced defects are corrected and separately reviewed; never weaken it for CI. The synthetic grant is fake token/identity transport support; no Google hostname is contacted. Domain verification calls only an explicitly allowlisted loopback HTTP server. Native SQL and recorder counts are independent of the application's response assertions. Raw logs/receipts/screenshots remain ignored; sanitized counts, source SHAs and hashes are committed in SAFE_ACCEPTANCE_RECEIPTS.json. No customer data or credentials were read.

Rollback: this continuation changes tests/evidence only; no schema/runtime migration. Preserve original uncertain jobs and restore artifacts, never blind-replay POST or switch a PostgreSQL writer to stale SQLite. Stop the temporary fixture and remove only owned labelled containers after saving evidence; existing application containers are untouched.
