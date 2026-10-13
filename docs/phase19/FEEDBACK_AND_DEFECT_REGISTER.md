# Pilot feedback and defect register

No customer enrolled or invited; no real-world feedback collected. Empty feedback is not successful adoption.

| Severity | Issue | Owner / disposition |
|---|---|---|
| P1 fixed | Concierge blocked/unknown mail omitted from operator projections | Engineering; reproduced0vs2, corrected shared statuses, tenant/redaction regressionPASS |
| P1 fixed | Unknown Calendar intent lacked an execution receipt | Engineering; reproduced0vs1, added one redacted failed tool receipt; no replay |
| P0 fixed in18 | Provider times mismatch / offset reminder selection / booking-memory retention | Engineering; failing regressions before fixes; maintained in corpus |
| P0 gate | Real public Calendar/mail/reminder acceptance | Owner+engineering; exact scoped authorization and provider/human receipts pending |
| P0 gate | External pilot owner/participants/accounts/dates/support/consent | Owner; unset, no activation permitted |
| P1 gate | Public browser/device/a11y/slow-network evidence | Owner/tester; scope/device access pending |
| P1 limitation | Interrupted sending watchdog and deployed DR | Engineering; no blind retry; real crash/recovery drill pending |
| P1 limitation | Actual model/token/provider/hosting costs and statistical task quality | Engineering; unavailable, no invented threshold pass |

For approved future feedback: record capability,locale,redacted receipt/test ID,severity,owner,disposition; avoid raw sensitive transcripts. Promote only reproducible reviewed failures into existing corpus.
