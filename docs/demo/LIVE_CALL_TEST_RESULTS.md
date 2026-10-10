# Live call results — one correct English business journey, acceptance incomplete

**One correct-details English SIP business journey passed. Bulgarian confirmation and three consecutive accepted journeys did not pass. Demo and production readiness are not claimed.**

Later Phase 7D testing provisioned the owner-supplied GCS model and local speech services. Windows PJSUA 2.17 registered extension 1001 (200) and called extension 2000 (CONFIRMED). Asterisk/ARI created a persisted session. These are actual signaling results. Earlier missing-model preflight findings are superseded.

Initial media attempts were silent because Asterisk advertised an unreachable Docker address. Endpoint media_address=127.0.0.1, bind_rtp_to_media_address=no and rtp_symmetric=yes corrected local routing. The corrected attempt at 2026-10-08T22:47:28Z (2026-10-09 01:47:28 Europe/Sofia) transmitted approximately 1.3K packets / 208.6 KB. Its received WAV lasted 26.08 seconds, with 7,924 nonzero samples and peak amplitude 19,836. Synthetic caller audio overlapped the greeting, so it is a partial greeting, not a complete business response. Hangup ended the session; owned channels/audio sessions returned to zero. Evidence: artifacts/local-demo/sip-tests/call-establishment.json and received-greeting.wav. These latest-result artifacts replace earlier helper receipts; the failures remain recorded here.

At the initial media-test stage, no complete journey had passed. Later English completion is recorded below. Caller-heard/human intelligibility and visual dashboard verification remain pending. Seeded appointments and fixture tests do not satisfy live acceptance.

Automated verification uses synthetic provider responses and tiny artifact fixtures. It covers shared Qwen routing, both agents, bilingual intent/confirmation/persistence, cancelled/mutated proposals, token receipt preservation after business rollback, quota rejection before inference, tenant scope, call ID preservation, explicit language switching, next-Monday/3-PM handling, available alternatives, demo seed/reset, local-only speech configuration, PCM/μ-law sample rates, RTP sequencing/backpressure, trusted ARI routing and owned synthetic lifecycle cleanup. This is not real speech/model/SIP acceptance.

Final suite/build/source results are recorded in PHASE7_READINESS_AUDIT after completion. Initial Phase 7 baseline: 177 backend tests passed in 47.005 seconds. An intermediate 192-test suite passed in 55.616 seconds. Frontend has 9 passing tests; initial lint identified Vue formatting warnings, which were corrected before the final check.

For each actual live attempt, record timestamp/timezone, locale, call duration, expected and actual STT, agent/tool result, persisted booking ID, first audible/end-to-end latency, error count and final outcome. Preserve redacted diagnostic evidence and corrective action for failures. Never populate an ID, transcription, duration or success row without the actual test.

| Required live scenario | Status |
|---|---|
| Bulgarian greeting/booking | Real proposal verified; confirmation failed |
| English booking | Correct-details SIP business workflow verified; human/visual acceptance pending |
| Locale switch with preserved context | NOT_RUN |
| Occupied-slot alternatives/conflict prevention | NOT_RUN |
| Barge-in and stale-response cancellation | NOT_RUN |
| STT/TTS/LLM failure recovery | NOT_RUN |
| Basic hangup/resource cleanup | OBSERVED on real call; broader failure recovery pending |
| Three consecutive successful booking journeys | FAILED |

## Actual final-configuration attempts

All rows below come from actual Windows PJSUA media and persisted backend activity. Fixtures are synthetic voices; transcripts are not injected into the live API. Call source is Asterisk. Caller audio and received WAVs are retained under artifacts/local-demo/sip-tests/<attempt_id>.

| Attempt / UTC | Locale | Actual result |
|---|---|---|
| 20261009T000413Z-53b018, 000432Z-9835a7, 000452Z-d895ae | BG / EN / BG | Three calls connected/received audio; the initial harness failed to locate sessions through cross-runtime SQLite reads and did not advance the speech journey. Switched to authoritative backend API. |
| 20261009T000726Z-78665f | BG | Request failed with timeout; no appointment. |
| 20261009T000812Z-9a8cc1 | EN | Tool checked 03:00 after truncated “3 p.” was mishandled; unavailable and later timeout. Exact AM/PM abbreviation support corrected this; no guessed afternoon time. |
| 20261009T001011Z-03e6ab | BG | Provider error; no appointment. |
| 20261009T010833Z-729b6e | BG | Reached need_date; ended with timeout; no appointment. |
| 20261009T011023Z-27dcc9 | EN | All three business states and response packets; persisted wrong surname Jane Deemle instead of Jane Demo. Golden validation failed. Appointment faef548d-e4a9-440f-92cf-74201012e1e0 was cancelled through authorized CancelAppointment/approval, preserving original data/audit. |
| 20261009T011352Z-219705 | BG | Reached need_date; timeout; no appointment. |
| 20261009T014217Z-0ac727 | BG | Correct Monday 15:00, 30-minute proposal for Мария Демо; confirmation transitioned to cancelled, then idle timeout. No appointment. Live raw transcription was not retained with transcript storage disabled, so no unsupported explanation of the cancellation is claimed. |
| 20261009T014627Z-182079 | EN | Correct-details business workflow passed: Jane Smith, 2026-10-12 15:00 Europe/Sofia, 30 minutes. Appointment 17b331e6-fda5-4735-8f88-1fd45d0e7b31 persisted; response packets observed; clean ended session. Human-heard/visual acceptance pending. |
| 20261009T014949Z-972bcc | BG | Correct Monday 16:00, 30-minute proposal for Мария Демо. Confirmation transitioned to cancelled; later idle timeout, no appointment. |

Latest English request/name/confirmation business-state observation latencies: 48,657 / 34,531 / 24,766 ms. Recording duration: 198.02 seconds, 169,787 nonzero samples, peak amplitude 11,388. First nonsilent recording offset: 17,881.375 ms, which is not synchronized first-audible latency. The harness verifies the proposed details before transmitting affirmative consent; mismatches withhold confirmation. New attempts preserve caller WAV/hash evidence alongside their results.

The isolated updated corpus recognized English Jane Smith/Yes confirm exactly. Bulgarian confirmation was “Путвърждавам часа” and remains outside the exact affirmative phrase gate. Punctuation/spacing normalization does not edit letters, drop negations or accept questions. Only one correct-details SIP business journey is verified at this point; none of these results establishes production readiness. Visual dashboard inspection was blocked by browser security policy; the stored booking and frontend API contract do not substitute for a visible UI check.

Final cleanup check: zero active Asterisk channels/calls, zero active backend CallSessions, active_voice_sessions=0 and audio_queue_depth=0. The correctly named English booking remained confirmed through the authenticated API. Evidence: artifacts/local-demo/final-persistence-cleanup.json. Twelve serial harness calls are retained in per-attempt directories across four runs (three initial lookup failures, six earlier speech/validation failures, then the final BG/EN/BG run). These counts are attempts, not successful journeys. Scoped shutdown was tested earlier with caches/database preserved and unrelated containers left intact; final services are kept running for human review.
