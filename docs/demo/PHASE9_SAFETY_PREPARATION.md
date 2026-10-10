# Phase 9 prerequisite recovery — 10 October 2026

Decision: **DEMO_BLOCKED**. This is preparation evidence, not release certification.

## Source checkpoint

The initial local preparation commit is `40483dc479c3d1f362bd8961407df24877861956`. Its Git history was scanned with Gitleaks: one commit, zero findings. It removes the missing-source-commit blocker. No release tag, remote push or public release was created. Subsequent preparation changes need their own reviewed checkpoint before an RC is frozen.

## Independent fixes

- Explicit Bulgarian/English month-name dates with literal day and year normalize to ISO. Missing years are not inferred; invalid calendar dates require clarification. Existing numeric/ISO dates remain supported.
- The existing bounded dashboard poll now refreshes bootstrap counts from persisted data, rather than leaving metrics at their initial value. No events or bookings are fabricated.

## Optional keypad guard

`VoiceConfig.booking_confirmation_mode` defaults to `speech`. The new `keypad` mode is **not activated or deployed**. The owner was asked to choose it; no response has been received.

In this mode, speech/ASR cannot authorize CreateAppointment. A proposal remains pending until an accepted SIP channel sends 1 after its proposal playback finishes, or sends 0 to reject. The private ARI event path accepts only bound call channels, the expected application, supported digits and bounded durations; it preserves the server-observed receive timestamp. Early/queued-before-arming tones, changed proposals, expired approvals, revoked permissions and ended calls cannot book. Replay creates no second appointment. The existing executor, tool authorization, availability, transaction and idempotency paths remain. Voice message bodies retain the existing privacy redaction behavior.

Language switching repeats the same proposal in the new voice locale before arming again. No new ASR, TTS or LLM model was downloaded or substituted. No actual DTMF/SIP acceptance rehearsal was performed. Unit/channel fixtures are not real tone or caller-heard evidence.

Primary protocol references: [Asterisk ARI DTMF events](https://docs.asterisk.org/Configuration/Interfaces/Asterisk-REST-Interface-ARI/Introduction-to-ARI-and-Channels/ARI-and-Channels-Handling-DTMF/) and [PJSIP DTMF transport](https://docs.pjsip.org/en/latest/specific-guides/sip/dtmf.html). Asterisk reports the channel/digit/duration; PJSIP requires negotiated telephone-event capability for RFC 4733 tones. Actual negotiation must be checked in a real rehearsal.

## Fixed-date speech failures retained

The unchanged BG38/MioCodec and small/int8 speech workers were probed with synthetic 8 kHz PCMU date requests. Numeric-date baseline: all three BG/EN/BG probes lost required date/time anchors. Spelled-number ablation: English correctly returned “October 13, 2026 at 4 p.m.”; both Bulgarian probes failed. One returned day 30/year 2020, another hour 70. No spelling/number repair, year injection or guessed date was used to force success, and no booking writes occurred.

These round trips cannot independently distinguish TTS articulation from STT recognition loss; human listening remains necessary. Data: `artifacts/phase9/fixed-date-speech/` and `fixed-date-speech-spelled/`, with actual WAVs/transcripts/timings. They are synthetic probes, not attended calls or representative human speech acceptance.

## Owner acceptance outstanding

The owner confirmed availability for an attended rehearsal but said the previous recordings and dashboard were not yet reviewed. The three actual caller-side excerpts and corresponding Appointments/Calls links were presented again. Their review remains unverified. The confirmation-mode question remains pending; elapsed time is not approval. The current running demo remains on its previously deployed speech flow.

To complete Phase 9: obtain the mode choice; correct and verify fixed-date Bulgarian speech; obtain actual human listening/dashboard evidence; perform three consecutive attended journeys; then explicitly authorize and verify demo archival reset/restart. Do not label these missing mandatory gates as noncritical limitations.

Fresh verification: 243 backend tests passed in 51.418 seconds; 10 optional-keypad tests are included. Frontend nine tests, lint, typecheck and build pass. Source boundary check: 172 files, zero failures. These checks do not replace a real DTMF/SIP or human listening rehearsal.
