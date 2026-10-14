# Security and recovery checkpoint

New local P0 fix centralizes widget text-copy redaction for clear and retention: messages/provider receipts plus agent/tool/approval arguments, outcomes, results and handoffs. Pending approvals cancelled; appointments preserved. New regression verifies another conversation and tenant, including identical conversation ID, remain untouched. All18widget tests PASS,9.466s after correcting an invalid cross-tenant test fixture that was rejected by the existing foreign key.

Initial sandboxed test invocation stalled and was cancelled; escalated synthetic run completed. It is not recorded as a pass. Source checker238files/0failures; git diff whitespace check passes. Full backend results recorded separately when complete.

This fix is chat-text erasure, not full tenant/contact/upstream erasure or legal compliance. Business request/event records and pseudonymous audit have separate retention. Existing generic privacy service remains responsible for explicit broader erasure.

Full backend329testsPASS,95.973s; evidence `artifacts/phase17/backend-tests.txt`. Existing CI executes the versioned offline corpus and uploads only redacted results. No hosted CI or new dependency vulnerability result is claimed.

Existing isolated encrypted SQLite restore/tamper/no-overwrite tests are historical offline evidence, not deployed recovery. New host backup/restart/worker crash drills require scoped remote approval and a nonlive restore target with provider dispatch disabled. Preserve original key and data, no live overwrite.
