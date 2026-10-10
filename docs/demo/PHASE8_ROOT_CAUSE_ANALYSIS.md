# Phase 8 root-cause audit — 9 October 2026

Status: investigation in progress; no new live acceptance claimed. Scope is the existing test_mid voice path only.

## Correlated baseline

Failed Bulgarian attempt: 20261009T014217Z-0ac727; call c9f17c4f-4046-4f40-80a3-b4ba4a562b14; conversation 22fb8534-cf62-4777-84c7-af498f3b6981; tenant smilecare-demo. It reached a correctly named/timezoned Monday 15:00 proposal for Мария Демо, then transitioned to cancelled during the confirmation turn and ended with timeout. No appointment was created. The raw live transcript was intentionally not retained, so the precise words that caused cancellation cannot be recovered from that artifact.

Successful English business attempt: 20261009T014627Z-182079; call 4ad9be41-0fb1-42fd-8154-3289121bf373; appointment 17b331e6-fda5-4735-8f88-1fd45d0e7b31; Jane Smith, 12 October 2026 15:00 Europe/Sofia, 30 minutes. All three states and response packets were observed; data survived backend restart. Human intelligibility and visual dashboard acceptance were not established by that result.

Evidence: per-attempt result.json, resources.json, received.wav and redacted PJSUA logs in artifacts/local-demo/sip-tests; restart-persistence-results.json; final-persistence-cleanup.json. Historical synthetic cases are separate from live transport evidence.

## Symptoms, hypotheses and minimal plan

| Layer | Observed evidence | Hypothesis / smallest next step | Regression / acceptance |
|---|---|---|---|
| SIP/RTP | Registration/CONFIRMED and nonzero 8 kHz recordings; earlier SDP address failure was fixed | Preserve working routing; measure sequence/codec/playback independently | Existing RTP parser, peer isolation, teardown tests plus actual call recording |
| VAD | TurnBuffer starts retaining samples only after RMS >=400; no pre-roll | Quiet initial consonants or short negations may be clipped. Compare full synthetic WAV with finalized buffer before patching | Replay exact frames; verify onset preserved, final emitted once, bounded memory |
| STT | Existing small/int8/beam1/single-worker corpus produced weekday/name/affirmation errors | Separate TTS articulation from preprocessing/language selection; replay full versus VAD audio with explicit bg/en | Required five Bulgarian utterances; record raw text/entity accuracy/timing |
| Language | Initial voice STT may autodetect; later locale is preserved; explicit switch exists | Verify first-turn hints and explicit preference without forcing a switched caller back to Bulgarian | BG→EN state/handoff/error tests and real switching audio |
| Booking consent | Literal gate rejects corrupted words; required reservation phrase is absent | Add only clear required affirmative phrases; never fuzzy-repair negations or names | Required affirmative passes; negative/question/corrupt forms fail |
| Model intent | Bulgarian confirmation became cancelled; live raw text absent | Do not claim the model or ASR alone caused it. Record synthetic turn decisions in scoped diagnostic evidence; prevent inferred cancellation without explicit caller cancellation | Unclear confirmation retains proposal; explicit cancellation works |
| TTS | Actual BG38/MioCodec synthesis exists; some generated phrases transcribe badly | Test required waveforms and existing generic references before considering replacement | Actual WAV/PCMU output, names/dates/numbers, independent playback and human listening |
| Performance | Qwen reached 4 GiB cap; memory-max events, no OOM; large stage delays | Inspect resident/cache/swap and CPU before adjusting existing flags; no 8B or paid provider | Actual stage/cgroup metrics; no claimed 2s/4s guarantee |
| Evidence | Privacy-off transcripts correctly redacted; several latest-result files were overwritten | Keep recording-off defaults; immutable synthetic run directories and content-free stage timing | No real caller text/audio retained by default; reproducible per-run evidence |

## Current runtime preflight

The first Phase 8 Docker query failed because dockerDesktopLinuxEngine was absent. Docker Desktop start was requested through its installed CLI; startup is not yet proof that services or calls work. No working infrastructure or agent framework is rebuilt by this audit. A major TTS model replacement requires owner approval under the Phase 8 request.

## Prioritized patch sequence

1. Reproduce full/VAD-transcribed audio and measure onset/endpoint loss.
2. Add bounded pre-roll only if the replay confirms clipping; preserve queue/utterance limits.
3. Support the required explicit reservation confirmation and protect cancellation from model-only guesses.
4. Evaluate installed TTS on required Bulgarian phrases; retain its adapter and license provenance.
5. Instrument synthetic diagnostic runs, then BG/EN/BG actual SIP attempts with immutable records and proposal checks.
6. Run regressions, validate persistence/cleanup, and leave unmet human/audio/dashboard gates marked PARTIAL / BLOCKED.

## Phase 8 measured outcome — 9 October 2026

The runtime recovered through the existing Docker Desktop CLI and project-scoped Compose startup. Only the backend image was rebuilt for targeted fixes; the existing Qwen, STT and TTS models were preserved.

Actual frame replay confirmed two defects: missing quiet onset and one booking request split into two turns by the old 600 ms endpoint. A bounded 200 ms pre-roll and a demo-only 1800 ms silence setting retain one turn in all seven saved fixtures; 1200 ms still split Bulgarian. The platform default is preserved. Clear required Bulgarian reservation confirmation is supported. Model-only cancellation guesses now retain the proposal and request clarification unless literal caller cancellation is present. The name guard excludes the recognized standalone prefix “са”. Negations, questions and corrupted affirmative phrases are not repaired into consent.

The required synthetic corpus still fails Bulgarian clock and confirmation recognition. Windows Ivan evaluation recognized the clock correctly at original 16 kHz, then failed after 8 kHz PCMU conversion; bandlimited upsampling did not restore it. This is evidence of narrowband recognition loss, not proof that the live caller said any particular transcript. TTS replacement alone is insufficient.

208 backend tests passed in 57.674 seconds; frontend typecheck/lint/nine tests/build passed; 158 source/config files passed the boundary check. A network-disabled redacted Gitleaks scan of 249 staged source/config/docs files found no leaks. Host memory pressure and unrelated background workloads limit performance conclusions.

**PARTIAL / BLOCKED.** Three real SIP attempts finished, but the booking release gate did not pass. Registration, call establishment and response packets are separate from caller-heard confirmation. Known locale was selected through the existing authenticated call-language control; no STT transcript was injected. Synthetic WAV callers were used, not representative human callers. Raw live transcripts remain disabled by the existing privacy settings.

| Locale | Attempt | Call ID | Last booking state | New confirmed bookings | Request/name/confirm observation ms |
|---|---|---|---|---|---|
| bg-BG | 20261009T100552Z-92117b | 7231118e-9424-4daa-a87a-3e3a46279cc4 | awaiting_confirmation | 0 | 33484/44953/68437 |
| en-US | 20261009T100926Z-58c039 | 1b8ef3fe-c435-46ec-94a3-a6b57cd11df5 | awaiting_confirmation | 0 | 26110/30734/73907 |
| bg-BG | 20261009T101251Z-931cd0 | 099194ab-20ff-44b1-90fd-a5afa9b292d6 | awaiting_confirmation | 0 | 29609/41047/68281 |

Each attempt retains its input hashes, received WAV, redacted signaling, resource samples, conversation, agent handoffs and tool results under artifacts/phase8/sip-tests/<attempt>/. The summary is artifacts/phase8/three-call-results.json. State observation timings include input playback, buffering, inference and polling; they are not synchronized first-audible latency. No new correct booking or three-call success is inferred. The prior correct English booking remains historical evidence, not a Phase 8 pass.

Required remaining gates: reliable telephone-band time/consent recognition, caller-heard intelligibility, real in-call language switching/unavailable/interruption/failure scenarios, visual dashboard verification and three consecutive complete correct bookings. Existing unit tests do not establish those live gates. Browser security policy rejected local dashboard inspection; no indirect or alternate-browser bypass was attempted.

## Phase 8B measured update — 9 October 2026

Implemented the smallest confirmation fix: exact clear consent in an existing unexpired proposal is decided deterministically, without a second probabilistic intent veto. Executor/tool/approval authorization, fingerprint/expiry, availability and idempotency checks remain. Rejection, explicit requested slot replacement, voice expiry and disconnect invalidate an outstanding proposal; playback, segmentation, handoff and short silence retain it. Ambiguous text explicitly asks for clarification. Web Chat HTTP expiry behavior is preserved.

Content-free bounded tenant traces correlate all supported stages. Local STT is final-only; partial_supported=false is explicit. Nine new regression tests cover durable single execution/replay, rejection, ambiguous/question transcripts, expiry, requested changes, locale retention, trace privacy/tenant bounds, disconnect cancellation and rollback-safe persistence tracing. The initial full suite passed 216 tests in 47.318 seconds; the final report below reflects any later trace correction. Focused finalized voice/confirmation regressions passed 41 tests in 10.400 seconds. An earlier 215-test full run also passed; the initial targeted web expiry regression was corrected before deployment. Only the backend image was rebuilt; no inference models or working infrastructure were rebuilt.

Acoustic recovery remains partial. Twenty-seven actual PCMU trials found a question waveform transcribed as literal consent. Deterministic text safety does not fix ASR loss of interrogative meaning. No broad keyword, fuzzy spelling, negative-word dropping or expected-transcript injection was introduced. General speech consent safety and human/live verification are not claimed.

**PARTIAL / BLOCKED.** Deterministic confirmation is recovered; complete live acceptance is not inferred. The owner declared availability for live acceptance before new SIP attempts. Caller fixtures combine existing BG38 speech and authorized Ivan evaluation speech; the assistant's response provider remains BG38. Known locale is selected through the existing authenticated control, without transcript injection.

| Locale | Attempt | Call ID | Business workflow | Booking IDs | Human-heard verification |
|---|---|---|---|---|---|
| bg-BG | 20261009T105422Z-29fa08 | 38d1e640-f178-4b59-a901-021bbd8103e8 | True | e1918d21-a585-4b07-85dc-2947b037c450 | pending |
| en-US | 20261009T105839Z-e5d106 | 8c3cb1f5-ab9e-4853-890a-6180ed1a0e11 | True | 4c04be6e-27f1-4925-9737-3f6c7ff79a91 | pending |
| bg-BG | 20261009T110159Z-7f0d1a | 33c8e022-7c76-4ad2-a4c6-765caebd2c62 | True | f170806c-a94b-4c58-9379-cae95c27e9e2 | pending |

Three consecutive complete calls, human-audible correct confirmation, visual dashboard evidence and the acoustic question false-positive control remain open gates. Received RTP/nonzero WAV/persisted row alone cannot satisfy human acceptance. New receipts are artifacts/phase8b/sip-tests/<attempt>/; prior unsuccessful attempts remain in Phase 8 evidence. Sequence continuation is permitted only after the preceding business journey passes; no failure is silently omitted. Browser policy previously blocked local inspection and is not bypassed; the owner can verify the dashboard directly.

All three consecutive selected-affirmative SIP business journeys passed. Each created one distinct correct appointment, and response audio reached the caller transport. All three survived the targeted backend restart; no active API calls or Asterisk channels remain. Caller-side final-45-second excerpts were provided for human listening. This is business/transport evidence, not full human acceptance.

The owner initially reported ERR_CONNECTION_REFUSED when checking the dashboard. The intended URL is http://127.0.0.1:3011/dashboard; the existing listener was verified on 127.0.0.1:3011 and returned HTTP 200. Visual booking verification remains pending the owner’s follow-up; HTTP availability is not visual proof.

Latest complete backend suite: 217 tests passed in 57.213 seconds.

Preserved frontend verification: typecheck, zero-warning lint, nine tests and build all passed, including source/bundle environment-secret scans. Source boundary check and final staged secret scan results are recorded separately. Final backend is healthy with rollback-safe trace; the three bookings survived its restart. The current Qwen/STT/BG38 model services remain unchanged.
