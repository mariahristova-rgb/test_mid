# Reproduced defects and privacy/security verification

13October2026. Fixed locally, without deployment:

| Severity | Defect | Reproduction and resolution |
|---|---|---|
| P0 | Confirmed provider event had different start/end from requested slot | Two new tests failed before fix; validate aware returned times/identity before local create/reschedule success; mismatch raises delivery_unknown |
| P0 | Mixed UTC/Sofia offsets delayed due reminders | Bilingual lifecycle failed to send due reminder; worker now compares/orders julianday values rather than ISO text |
| P0 | Clear chat retained uncommitted visitor name in booking_state | New regression failed before fix; shared erasure clears booking_state for clear/retention while retaining appointments |
| P1 | Empty corpus could return successful zero-case execution | Fail-closed validation rejects empty/duplicate/unsupported/malformed sets; skipped/missing/multiple loaded tests fail; redacted receipt testsPASS |

New concurrent mock-intent checks demonstrate serialization and one booking for competing slot actions within one process. This is not distributed-lock/HA evidence. Information-email test supplies required synthetic name/email and verified owner; initial incomplete fixture was rejected by existing schema and corrected without loosening validation.

Remaining defect: Health/Quality/Operations projections omit concierge `delivery_unknown` and `blocked` job statuses. Investigated source references: customer_workspace.py health/suggestions and saas_api.py operations. P1 operator visibility assigned to Phase19 local plan; provider state itself remains persisted and is not mislabeled as delivered. No raw real job data was accessed.

No secrets/tokens/transcripts exported into evaluation artifacts. Latency scope is test execution including fixture setup. Financial records, actual provider events and broader personal data have separate retention/owner-controlled erasure; no legal certification.
