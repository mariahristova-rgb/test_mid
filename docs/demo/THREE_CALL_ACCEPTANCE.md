# Three-call release gate — Phase 8

Required order: Bulgarian, English, Bulgarian at another available time. Current status: NOT PASSED. No consecutive streak is inferred from fixtures, a previous English booking, or service health.

Command: .venv/Scripts/python.exe scripts/test_phase8_voice_calls.py

Evidence is stored under artifacts/phase8/sip-tests/<UTC-attempt-id>/ with actual caller WAVs/hashes, receive recording, redacted signaling log, persisted state/tool/agent data and resource samples. The summary is artifacts/phase8/three-call-results.json. Missing human-heard or dashboard evidence remains unverified even if business-state checks pass.

The first invocation failed before making a call because the wrapper lacked the repository import path. That harness defect was corrected; it is not counted as a SIP pass. Subsequent actual results are appended when the run finishes. Any failure breaks the streak; the failure remains retained and the sequence must restart after a demonstrated correction.

## Phase 8 measured outcome — 9 October 2026

**PARTIAL / BLOCKED.** Three real SIP attempts finished, but the booking release gate did not pass. Registration, call establishment and response packets are separate from caller-heard confirmation. Known locale was selected through the existing authenticated call-language control; no STT transcript was injected. Synthetic WAV callers were used, not representative human callers. Raw live transcripts remain disabled by the existing privacy settings.

| Locale | Attempt | Call ID | Last booking state | New confirmed bookings | Request/name/confirm observation ms |
|---|---|---|---|---|---|
| bg-BG | 20261009T100552Z-92117b | 7231118e-9424-4daa-a87a-3e3a46279cc4 | awaiting_confirmation | 0 | 33484/44953/68437 |
| en-US | 20261009T100926Z-58c039 | 1b8ef3fe-c435-46ec-94a3-a6b57cd11df5 | awaiting_confirmation | 0 | 26110/30734/73907 |
| bg-BG | 20261009T101251Z-931cd0 | 099194ab-20ff-44b1-90fd-a5afa9b292d6 | awaiting_confirmation | 0 | 29609/41047/68281 |

Each attempt retains its input hashes, received WAV, redacted signaling, resource samples, conversation, agent handoffs and tool results under artifacts/phase8/sip-tests/<attempt>/. The summary is artifacts/phase8/three-call-results.json. State observation timings include input playback, buffering, inference and polling; they are not synchronized first-audible latency. No new correct booking or three-call success is inferred. The prior correct English booking remains historical evidence, not a Phase 8 pass.

Required remaining gates: reliable telephone-band time/consent recognition, caller-heard intelligibility, real in-call language switching/unavailable/interruption/failure scenarios, visual dashboard verification and three consecutive complete correct bookings. Existing unit tests do not establish those live gates. Browser security policy rejected local dashboard inspection; no indirect or alternate-browser bypass was attempted.

## Phase 8B measured update — 9 October 2026

**PARTIAL / BLOCKED.** Deterministic confirmation is recovered; complete live acceptance is not inferred. The owner declared availability for live acceptance before new SIP attempts. Caller fixtures combine existing BG38 speech and authorized Ivan evaluation speech; the assistant's response provider remains BG38. Known locale is selected through the existing authenticated control, without transcript injection.

| Locale | Attempt | Call ID | Business workflow | Booking IDs | Human-heard verification |
|---|---|---|---|---|---|
| bg-BG | 20261009T105422Z-29fa08 | 38d1e640-f178-4b59-a901-021bbd8103e8 | True | e1918d21-a585-4b07-85dc-2947b037c450 | pending |
| en-US | 20261009T105839Z-e5d106 | 8c3cb1f5-ab9e-4853-890a-6180ed1a0e11 | True | 4c04be6e-27f1-4925-9737-3f6c7ff79a91 | pending |
| bg-BG | 20261009T110159Z-7f0d1a | 33c8e022-7c76-4ad2-a4c6-765caebd2c62 | True | f170806c-a94b-4c58-9379-cae95c27e9e2 | pending |

Three consecutive complete calls, human-audible correct confirmation, visual dashboard evidence and the acoustic question false-positive control remain open gates. Received RTP/nonzero WAV/persisted row alone cannot satisfy human acceptance. New receipts are artifacts/phase8b/sip-tests/<attempt>/; prior unsuccessful attempts remain in Phase 8 evidence. Sequence continuation is permitted only after the preceding business journey passes; no failure is silently omitted. Browser policy previously blocked local inspection and is not bypassed; the owner can verify the dashboard directly.

All three consecutive selected-affirmative SIP business journeys passed. Each created one distinct correct appointment, and response audio reached the caller transport. All three survived the targeted backend restart; no active API calls or Asterisk channels remain. Caller-side final-45-second excerpts were provided for human listening. This is business/transport evidence, not full human acceptance.

The owner initially reported ERR_CONNECTION_REFUSED when checking the dashboard. The intended URL is http://127.0.0.1:3011/dashboard; the existing listener was verified on 127.0.0.1:3011 and returned HTTP 200. Visual booking verification remains pending the owner’s follow-up; HTTP availability is not visual proof.
