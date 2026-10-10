# Planned customer journey

**DEMO_BLOCKED — preparation only.** Phase 8B has not passed the mandatory human/speech acceptance gate. No release candidate is certified and no new Phase 9 live rehearsal, reset, public release or real notification was performed.

Versioned fixed plan: demo-plan.json, **13 October 2026**, Europe/Sofia, 30 minutes. Planned BG 15:00, EN 16:00 and repeat BG 17:00 are currently future/free for both fictional dentists under the existing seeded mock policy. Read-only audit created no reservation. This fixed-date voice rehearsal has not been performed; supported text forms are numeric/ISO and speech may not preserve them. Stop on a mismatched proposal rather than substituting “tomorrow” or guessing.

| Step | Existing implementation/evidence | Required live verification |
|---|---|---|
| Dial | Authorized loopback SIP endpoint 1001 dials extension 2000; Asterisk/ARI resolves SmileCare/default | New attended registration/routing/audio; no public carrier claim |
| Greeting | Seeded BG/EN SmileCare greetings; existing BG38 response provider | Intelligible first greeting, active voice locale |
| Request | Receptionist, locale/state, missing date/name collection | Unambiguous fixed date/time and verbatim synthetic name |
| Handoff | Existing tenant/assistant/conversation/call/locale/intent/arguments/correlation handoff | Actual scoped execution details, no fabricated event stream |
| Availability | Existing mock calendar, Mon–Fri 09–18, two dentists/30 minutes | Free slot and unavailable branch; clearly say demo calendar |
| Confirmation | Phase 8B exact pending-context decision and permission checks | Reject questions/negatives/ambiguity; question ASR control remains failed |
| Persist | Transactional approval/tool/calendar path, one-per-call idempotency | Correct persisted ID and replay does not create another |
| Speak | Local TTS after business result; RTP output packets | Human hears correct name/date/time in active language |
| Dashboard | /dashboard, /assistants, /inbox, /calls, /appointments; call activity shows agents/tools | Human sees actual rows/status/timestamps; metadata-only voice history reflects privacy settings |
| Notification | Bilingual templates, offline mock scenario artifact | No live provider; only explicitly simulated preview, not delivered message |
| Reset/repeat | Confirmed demo-only archival maintenance, seed preservation | Owner-approved operational rehearsal after gate passes |

UI locale, conversation locale and voice locale are separate. An English UI preference must not change a Bulgarian call. No transcript storage or audio recording is enabled automatically to improve the demonstration; real caller retention needs the configured lawful basis/consent. Existing UI polling is bounded to two seconds, skips busy/overlapping work and reports errors; visual responsiveness remains unverified.
