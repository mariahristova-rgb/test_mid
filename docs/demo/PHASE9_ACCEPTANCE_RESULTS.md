# Phase 9 acceptance results

**DEMO_BLOCKED — preparation only.** Phase 8B has not passed the mandatory human/speech acceptance gate. No release candidate is certified and no new Phase 9 live rehearsal, reset, public release or real notification was performed.

## Prerequisite evidence checked

Phase 8B actual attempts: 20261009T105422Z-29fa08 (BG), 20261009T105839Z-e5d106 (EN), 20261009T110159Z-7f0d1a (BG). Golden business rows and response packets passed; three distinct appointments survived restart. Human-heard confirmation and visual dashboard fields remain false/pending. The question acoustic control failed. Earlier unsuccessful Phase 8 attempts remain retained.

- Human-heard Bulgarian and English confirmations remain unverified
- Actual dashboard call/conversation/agent/tool/booking visibility remains unverified
- Telephone-band ambiguity/negative/question recognition safety has not passed
- Fixed-date Bulgarian synthetic telephone speech probes failed; fixed-date attended voice rehearsal not yet verified

## Newly run preparation verification

243 backend tests passed in 55.353 seconds. Fresh frontend nine tests/typecheck/lint/build pass; actual logs are artifacts/phase9/frontend-*.txt. New reset and readiness tests use disposable stores; other/unmarked tenants and active calls are protected, seed fixtures survive repeated archival reset, and healthy/business evidence cannot waive human or acoustic gates. One new test initially referenced audit_records instead of the existing audit_events table; it failed and was corrected before the passing full suite. The original reset regression was updated to assert the now-required seed preservation behavior, not to bypass failed acceptance.

The read-only runtime audit returned DEMO_BLOCKED with database integrity ok, zero foreign-key errors, schema 5 and existing configured resources. Fixed future slots were checked using the current mock calendar rules and persisted appointment reads; no reservations were created. Four isolated offline messaging scenarios passed; no real send or live dashboard notification was produced.

## Not performed

No new Phase 9 live SIP calls, human listening certification, visual UI inspection, live reset, live restart rehearsal, provider send, RC branch/tag/commit, remote push or public deployment. Reset source changes are prepared, not deployed to the live image. This is not a new three-call acceptance streak or production validation.

Release decision: **DEMO_BLOCKED**. Do not relabel mandatory voice/persistence/UI failures as limitations. Obtain new actual evidence after correcting the prerequisite issues, then run the full release-candidate workflow.


## Latest prerequisite preparation

See [PHASE9_SAFETY_PREPARATION.md](PHASE9_SAFETY_PREPARATION.md). The initial Git checkpoint exists; the remaining blockers are human audio/dashboard acceptance, confirmation-mode selection and failed Bulgarian fixed-date speech probes. The optional keypad guard remains inactive and undeployed. Latest full suite: 243 tests passed in 51.418 seconds; frontend nine tests/typecheck/lint/build pass. No new live calls or reset were performed.
