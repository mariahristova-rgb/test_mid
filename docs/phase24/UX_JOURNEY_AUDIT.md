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
