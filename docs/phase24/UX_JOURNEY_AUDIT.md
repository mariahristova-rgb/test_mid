# Ontelyx journeys and acceptance gaps

13October2026. Source/fixture audit,not attended browser usability. Competitor patterns are documented separately. No runtime changes before plan approval.

| Requested scenario | Current verdict/scope | Friction and next evidence |
|---|---|---|
| BGowner completes setup | PASS APIfixture; NOTTESTEDhumanUI | New metadata/date picker exists; morning-hours mandatorypreview reproducedFAIL; representative slot + inline errors needed |
| ENowner editsFAQ | PASS existing synthetic contracts; NOTTESTEDhumanUI | Existing FAQeditor/save/revision; completion/focus/discard rehearsal needed |
| Owner previews before activation | FAIL valid morning config | Fixed15:00sample incompatible with09–12hours; disposable teststate remains safe |
| Website customer booking | PASSmock/live historical limited scope | Final public real journey/browser notaccepted; no invented receipt |
| Voice customer reschedules | BLOCKEDreal | Ownership/real speech/model/listening gates; no shared proof |
| Voice interruption | PASSfixture | speak/barge/replay keepsbooking; actual audio/latency NOTTESTED |
| Verified website→voice | BLOCKED | Proposed continuity contracts pending; no callerID shortcut |
| Human request | PASSsyntheticqueued | No live-available promise; distinguish queued/unavailable/failed in actualUI |
| Unknown booking recovery | PASScontract | No blindreplay; owner/customer retry/status comprehension NOTTESTED |
| Owner disablesvoice | Component controls only; dedicatedrehearsalNOTTESTED | Verify new-session rejection and committed booking preservation |
| Mobileassistivetechnology | NOTTESTED | Exact browser/device/screenreader/zoom/contrast/touch evidence absent |
| Localmodel unavailable | PASSprovider-failurefixtures; voiceconsoleNOTTESTED | No fake transcript/audio; explicit unavailable/stop/reset path needed |

Setupform source: normal Continue uses native submit validation; SaveDraft is typebutton and calls save directly. This is a source-identified validation-feedback risk,not yet a rendered-browser failure. Preserve native/server validation and allow draft/test/activation states to be understood; do not weaken schema to mask errors.

Pre-test rules for approved first increment: valid morning/default/holiday/multi-timezone config can run a representative booking; closed/unavailable actual slots still refused; rejection/ambiguity remain0bookings; no realappointments/emails; tenant/revision/API compatibility unchanged. Form errors must identify field/reason and preserve values; keyboard focus must return to actionable invalid control. No broad WCAG or usabilitytime target without actual device/sample evidence.

Model latency/concurrency,SLO/DR/cost and full businesscatalogue remain separate engineering gates; UX labels cannot certify them. Missing Phase22/23acceptance is not repaired by redesigning navigation or writing new statusdocs.


## Increment 1 resolution — 14 October 2026

The reproduced morning-hours preview defect is corrected locally. Preview selects a representative slot within 14 tenant-local days using the existing date parser and MockCalendarProvider.available; it excludes ambiguous/nonexistent DST starts/ends and duration-changing transitions. Occupied scenarios seed the selected slot. A changed synthetic reference clock preserves the relative “tomorrow” request; the actual reference/timezone remains visible. No slot yields BLOCKED/preview_no_slot, never a false PASS. FAQ/greeting/handoff do not depend on booking availability.

Save and Continue share native constraint checks before busy disables controls. Invalid controls receive aria-invalid and an error association, collapsed FAQ details open, and the first invalid control receives focus. Server errors focus the alert; failed step saves restore the previous step without discarding edits. Existing server validation stays authoritative. Status now distinguishes saved draft, mock-tested draft, activated Web Chat and simulated preview; latest receipt revision and saved-config hash match identify stale results after edits. Native/Node tests do not prove rendered or assistive-device usability.

Actual calendar rules, API request/response field contracts, schema 5, uncertainty handling and provider behavior are unchanged. See the evidence matrix for failures during execution, final commands/results, exact files and rollback. This does not establish Phase24 completion, UX GO or production GO.
