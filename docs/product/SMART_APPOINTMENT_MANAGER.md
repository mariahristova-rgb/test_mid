# Google lifecycle acceptance

11 October 2026. Local feature branch `codex/phase15-product-experience`; no Phase 15 push/merge/public deployment. Existing URLs and the two-agent runtime are retained.


Existing policy: primary owner calendar; Monday–Friday 10:00–19:00 Europe/Sofia; 30-minute demos, 15-minute buffer, cutoff 31 December2026. Existing configurable 2027 policy is covered by offline tests. No policy time/window changes were made.

Owner explicitly approved BG booking 53e2ffc5-7296-4fb6-b61f-71d177a11d9f-booking: 14 October15:00 →16:00 →cancel; all notification recipients mariya.manolova92@gmail.com. Signed-link public manage API checked availability with exact owned-event exclusion, conditional update/cancel and duplicate action cache. Google GET independently confirmed16:00 then cancelled; Appointments matches. Old/new reminder jobs are cancelled, management email is sent. Owner confirmed inbox receipt and Google cancellation notice.

Owner separately approved English create/cancel at14 October15:00. Booking728ba8b8-c018-4db0-93e2-a1b5cd85317d-booking persisted exactly once; Google readback confirmed creation/cancellation; duplicate replay prevented; management email sent and reminder cancelled. Human English inbox receipt remains open. No English reschedule or actual due reminder delivery is claimed.

Live operations were temporarily enabled only for named tests and restored off in finally blocks. No unrelated calendar events were touched. Initial BG script failed parsing a localized management link before mutations; corrected. English cancellation initially stopped before mutation because the test helper restored operations before its new management email was sent. Fixed receipt polling to inspect new due jobs, completed approved delivery/cancel and retained failure history.

Code: backend/assistant/{concierge,concierge_api,google_workspace}.py; scripts/phase15_approved_calendar_lifecycle.py, phase15_english_booking*.py; artifacts/phase15/english-live-booking-result.json. The original calendar create receipt remains in artifacts/phase14. Full production race recovery, reminder/inbox acceptance and public staging ownership links remain gates.
