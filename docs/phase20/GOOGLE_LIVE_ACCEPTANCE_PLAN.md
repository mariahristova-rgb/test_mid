# Exact proposed Google acceptance scope — NOT AUTHORIZED/EXECUTED

13October2026. Reuse concierge.py/google_workspace.py/persistent jobs; do not import local refresh tokens or alter a global production clock. Prior Phase15approvals do not authorize these new actions.

| Approval field | Proposed bounded value |
|---|---|
| Owner/account/calendar | mariya.manolova92@gmail.com; primary calendar, verify owner OAuth and configured blocking calendars |
| Calendar scopes | calendar.events.owned,calendar.freebusy,calendar.calendarlist.readonly plus openid/email identity |
| Gmail scope/sender/recipient | gmail.send; sender and sole attendee/recipient mariya.manolova92@gmail.com; no other recipients |
| BG slots |14October2026,15:00–15:30→16:00–16:30 Europe/Sofia, then cancel |
| EN slots |14October2026,17:00–17:30→18:00–18:30 Europe/Sofia, then cancel |
| Execution window/deadline |14October10:00–19:00Europe/Sofia; expire approval at19:00; host stop20:57 remains unchanged |
| Actions | Availability, email verification, explicit create, reschedule, cancellation, one scoped reminder acceptance per locale, controlled replay/readback |
| Notifications | Up to8Gmail test messages across both locales plus native Google attendee updates (up to6); verify exact content/recipient before owner approval |
| Cleanup | Cancel only newly mapped approved test events/jobs; restore operations flag off, retain redacted receipts, no real unrelated records erased |

These slots are proposals, not availability claims. If past/unavailable or host inaccessible, stop and revise for owner approval; never substitute another slot/account silently. Actual OAuth connection, refresh access, external reads/writes/sends and cleanup require explicit approval for this exact scope. Never broaden scopes or authorizations from an email address alone.

Acceptance: fresh FreeBusy before commits; explicit visitor email proof/confirmation; stable intent/event IDs and provider time/identity readback; dashboard persistence; forged/stale link refusal; one event under replay; native/custom notification status distinguished from inbox receipt. Controlled reminder clock semantics remain offline; one authorized actual reminder email may be sent within the real eligible interval, without globally advancing a live worker or processing unrelated jobs. Owner confirms receipt. Record queued/provider-accepted/unknown/failed separately.

If timeout/uncertain response: no second write/send; original intent/job identity persists, redacted trace reviewed and provider reconciliation separately authorized. Stop for tenant leak, unauthorized write, duplicate or misdelivery.
