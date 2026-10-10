# Bilingual live acceptance — Phase 8

Status: PARTIAL / BLOCKED pending current run results, Bulgarian clock/confirmation recovery, human audibility, dashboard visibility and approval for any major TTS replacement.

Historical correct English call/booking is verified by prior artifacts and restart persistence. Phase 8 does not count that as a new pass. New scenarios use actual timestamps and Europe/Sofia, fictional Мария Иванова/Jane Smith, existing model/agents and mock calendar. Scenario corpus and live attempt evidence are separate.

A/B/BG repeat: scripts/test_phase8_voice_calls.py sends actual WAVs through PJSUA/Asterisk, uses existing authenticated language-selection controls to prefer explicit locale, verifies proposals before confirmation and records actual states/IDs/received audio. It never injects STT text into a live call. The exact corpus still contains recognition failures, so no automatic release pass is justified.

C/D/E/F: existing regression tests cover explicit BG→EN context retention, unavailable slots/concurrency, stale playback/barge-in, timeouts/hangup and tenant scope. New actual audio for “Please continue in English” was recognized exactly by the known-en worker. This alone does not prove an in-call switch; new live switch, physical interruption, human playback and failure scenarios remain separate gates.

Earlier browser policy blocked local dashboard inspection. No alternate browser/raw-CDP/indirect UI bypass is used. Actual API persistence is necessary but is not visual dashboard evidence. Human verification or restored permitted browser access is required.

## Phase 8 measured outcome — 9 October 2026

**PARTIAL / BLOCKED.** Three real SIP attempts finished, but the booking release gate did not pass. Registration, call establishment and response packets are separate from caller-heard confirmation. Known locale was selected through the existing authenticated call-language control; no STT transcript was injected. Synthetic WAV callers were used, not representative human callers. Raw live transcripts remain disabled by the existing privacy settings.

| Locale | Attempt | Call ID | Last booking state | New confirmed bookings | Request/name/confirm observation ms |
|---|---|---|---|---|---|
| bg-BG | 20261009T100552Z-92117b | 7231118e-9424-4daa-a87a-3e3a46279cc4 | awaiting_confirmation | 0 | 33484/44953/68437 |
| en-US | 20261009T100926Z-58c039 | 1b8ef3fe-c435-46ec-94a3-a6b57cd11df5 | awaiting_confirmation | 0 | 26110/30734/73907 |
| bg-BG | 20261009T101251Z-931cd0 | 099194ab-20ff-44b1-90fd-a5afa9b292d6 | awaiting_confirmation | 0 | 29609/41047/68281 |

Each attempt retains its input hashes, received WAV, redacted signaling, resource samples, conversation, agent handoffs and tool results under artifacts/phase8/sip-tests/<attempt>/. The summary is artifacts/phase8/three-call-results.json. State observation timings include input playback, buffering, inference and polling; they are not synchronized first-audible latency. No new correct booking or three-call success is inferred. The prior correct English booking remains historical evidence, not a Phase 8 pass.

Required remaining gates: reliable telephone-band time/consent recognition, caller-heard intelligibility, real in-call language switching/unavailable/interruption/failure scenarios, visual dashboard verification and three consecutive complete correct bookings. Existing unit tests do not establish those live gates. Browser security policy rejected local dashboard inspection; no indirect or alternate-browser bypass was attempted.
