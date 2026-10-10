# Phase 9 acceptance results

**DEMO_BLOCKED — preparation only.** Phase 8B has not passed the mandatory human/speech acceptance gate. No release candidate is certified and no new Phase 9 live rehearsal, reset, public release or real notification was performed.

## Prerequisite evidence checked

Phase 8B actual attempts: 20261009T105422Z-29fa08 (BG), 20261009T105839Z-e5d106 (EN), 20261009T110159Z-7f0d1a (BG). Golden business rows and response packets passed; three distinct appointments survived restart. Human-heard confirmation and visual dashboard fields remain false/pending. The question acoustic control failed. Earlier unsuccessful Phase 8 attempts remain retained.

- Human-heard Bulgarian and English confirmations remain unverified
- Actual dashboard call/conversation/agent/tool/booking visibility remains unverified
- Telephone-band ambiguity/negative/question recognition safety has not passed
- Git has no commit; the working tree cannot be identified as a committed release candidate

## Newly run preparation verification

222 backend tests passed in 48.999 seconds. Fresh frontend nine tests/typecheck/lint/build pass; actual logs are artifacts/phase9/frontend-*.txt. New reset and readiness tests use disposable stores; other/unmarked tenants and active calls are protected, seed fixtures survive repeated archival reset, and healthy/business evidence cannot waive human or acoustic gates. One new test initially referenced audit_records instead of the existing audit_events table; it failed and was corrected before the passing full suite. The original reset regression was updated to assert the now-required seed preservation behavior, not to bypass failed acceptance.

The read-only runtime audit returned DEMO_BLOCKED with database integrity ok, zero foreign-key errors, schema 5 and existing configured resources. Fixed future slots were checked using the current mock calendar rules and persisted appointment reads; no reservations were created. Four isolated offline messaging scenarios passed; no real send or live dashboard notification was produced.

## Not performed

No new Phase 9 live SIP calls, human listening certification, visual UI inspection, live reset, live restart rehearsal, provider send, RC branch/tag/commit, remote push or public deployment. Reset source changes are prepared, not deployed to the live image. This is not a new three-call acceptance streak or production validation.

Release decision: **DEMO_BLOCKED**. Do not relabel mandatory voice/persistence/UI failures as limitations. Obtain new actual evidence after correcting the prerequisite issues, then run the full release-candidate workflow.

## Continuation — 10 October 2026

The existing demo containers were restored with --no-recreate --no-build --pull never after Docker became available. All prior three Phase 8B bookings remain confirmed and no call session is active. No reset, new SIP acceptance call, image replacement, model download or release certification occurred. The configured dashboard is http://127.0.0.1:3011/dashboard; port 3017 is not this scoped stack.

Reset now fails closed if Docker status cannot be verified, before Python/SQLite maintenance; a Windows subprocess regression executes the actual wrapper with a failed diagnostic. Readiness now requires all negative/rejection/ambiguous/question controls and registered SIP establishment/clean termination evidence. Missing evidence cannot become a pass.

Fresh full backend run: 224 tests passed in 111.824 seconds. The focused preparation suite passed 8 tests in 10.513 seconds, including the additional wrapper test added after the full run. Source check: 168 files, zero failures. Offline redacted secret scan: 283 files, zero findings. Frontend was unchanged; its prior Phase 9 checks are historical, not rerun today.

Current evidence: artifacts/phase9/readiness-20261010.json and continuation-20261010.json. Release remains DEMO_BLOCKED: human-heard/visual acceptance, acoustic question safety and a committed source candidate are still missing.
