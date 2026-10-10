# CPU voice latency — actual partial measurements, acceptance incomplete

Completed evidence: local batch TTS synthesis for four phrases (40.42–66.74 ms); actual values are in BULGARIAN_TTS_VALIDATION. This is not end-to-end latency.

Qwen converted and loaded. Actual short-greeting SSE probes: Bulgarian first visible token 979.91 ms / total 2101.22 ms / 3.33 reported completion tokens/s in one run; English 3048.73 ms / 5984.19 ms / 1.67 tokens/s. A later loaded-system run was slower: Bulgarian 1639.55 ms / 3378.27 ms / 2.07 tokens/s; English 2855.72 ms / 9273.32 ms / 1.08 tokens/s. These are small synthetic-text model probes, not voice-turn measurements; background workloads and build contention remained active.

Actual narrowband robotic-source STT ranged approximately 7.4–18.0 seconds and failed Bulgarian words/confirmations. Neural-source STT ranged approximately 7.2–12.9 seconds; Bulgarian request/name improved, short confirmation failed. Actual neural synthesis took about 2.1–9.8 seconds for tested phrases on CPU. First-audio and caller-audible end-to-end latency remain unmeasured. Peaks and three-call booking success remain pending; no failed result is converted into a success claim.

The implementation retains bounded audio queues/VAD, worker isolation, cancellation before/after inference, no automatic business-action retry and actual provider usage receipts. Newly fixed integration defects include cancellation while waiting for inference headers, empty-STT replay and call-date reference preservation. Native/model/SIP failure tests and real benchmarks will be recorded as they execute.

Compact protocol probe under concurrent speech evaluation: Bulgarian failed with timeout; English first visible token 6245.40 ms, total greeting 13008.68 ms, 0.77 reported completion tokens/s, with correct structured intent/native tool selection. Receipts: artifacts/local-demo/llm-benchmark-compact.json. CPU output compaction alone does not guarantee responsiveness. Missing usage and timeout durations are not invented.

## Later measured configuration

Linux model-volume cold startup: 61.688 seconds in the observed log, versus 158.592 seconds in the preceding host-bind run. These are separate runs with changing host workloads, not a controlled guarantee. Subsequent compact BG/EN structured intent/native tool probes both passed. Bulgarian greeting: first visible token 14,330.23 ms, total 16,418.67 ms, 0.43 completion tokens/s over total request time. English: 2,872.98 / 5,650.26 ms, 1.77 tokens/s. Native decoder-only throughput is not separately measured. The latest compact JSON replaces the earlier latest-result file; the earlier timeout and timing evidence remains recorded above. Future runs now archive timestamped receipts.

Actual bandlimited neural TTS API first received audio bytes (batch service, not streaming vocoder): Bulgarian request 9,189.03 ms, alternate request 11,194.55, name 3,031.71, short confirmation 1,910.80; English request 7,770.97, name 3,205.09, confirmation 3,296.15. A later fixture generation ranged 2,186.20–11,831.45 ms. Generated caller WAVs include two seconds of trailing silence to prevent looping; that padding is not synthesis latency. Current receipts: artifacts/neural-voice-audio/call-input/synthesis-results.json.

Four-thread/single-worker int8 STT with known locale on the updated padded telephone-band corpus ranged 5,731.77–8,856.99 ms HTTP wall time. Bulgarian request used the exact weekday spelling “понедельник,” mapped to Monday by an explicit dictionary synonym. The raw transcript is preserved. The name prefix “Казом се” is no longer automatically mistaken for part of the caller's name; model extraction must remain a verbatim substring. Bulgarian consent “Путвърждавам часа” remains rejected. English “Jane Smith” and “Yes, confirm” matched this corpus. These are synthetic speech measurements, not representative human speech acceptance.

The English SIP attempt at 2026-10-09T01:10:24Z reached all three business states and emitted response packets. Request/name/confirmation state-observation latencies were 45,234 / 44,391 / 25,328 ms. Its recognized surname was wrong (“Jane Deemle”), so the golden check failed. The 204.98-second recording contains 190,282 nonzero samples, peak 11,388. Its first nonsilent recording offset was 13,621.375 ms; this is not a synchronized caller-heard latency. The wrongly named synthetic appointment was cancelled through the authorized tool, preserving the original record/audit. No successful correct-details journey is inferred from that persisted row.

Later verified English business journey (20261009T014627Z-182079): request/name/confirmation state observations 48,657 / 34,531 / 24,766 ms; exact Jane Smith/date/time/duration matched and appointment persisted. Bulgarian correct-proposal attempt: 59,844 ms request, 50,625 name and 63,875 confirmation observation; confirmation cancelled, no appointment. These state timings include transmitted fixture/queue/polling time and are not first-audible timing.

An actual tenant operational snapshot during the repeat run recorded STT mean/max 11,638.58 / 17,812.49 ms (7 calls, 1 error), TTS 13,467.49 / 17,630.23 (6 calls), agent/business voice turn 23,393.27 / 40,717.46 (5 calls), final-utterance-to-first-business-output-packet 52,528.73 / 65,032.81 (4 responses), and cached-ack first packet 10,815.16 / 20,086.05 (5 acknowledgements). The configured acknowledgement delay is six seconds; actual observed delivery exceeded it. Report the observation rather than claiming a guaranteed six-second response. Snapshot is cumulative for that backend lifetime and not per-call percentile data. Host regression tests and unrelated workloads were active during portions of these trials. Evidence: artifacts/local-demo/voice-operations-final.json.

Final Bulgarian 16:00 attempt (20261009T014949Z-972bcc): request/name/confirmation state observations 53,406 / 49,563 / 63,125 ms. Correct proposal matched; confirmation cancelled and call ended with timeout after 235.415 seconds. No booking was created. Final per-attempt logs, WAVs and resource samples remain distinct; no aggregate is used to imply three-call success.

## Phase 8 measured outcome — 9 October 2026

Actual Phase 8 synthetic corpus: STT HTTP wall time 4,863–7,224 ms; existing batch TTS total 1,764–13,819 ms. These ranges cover fourteen mixed Bulgarian/English synthetic cases, not a human recognition benchmark or streaming vocoder. Receipts: artifacts/phase8/speech-corpus/results.json.

Real compact Qwen structured probes passed in both languages. Bulgarian first visible token 17,735.45 ms / total 20,065.52 ms / 0.349 completion tokens per second over request wall time; English 5,314.64 / 8,403.25 / 1.190. Timestamped compact receipts are preserved in artifacts/local-demo. These are observed CPU requests under host memory/background load, not isolated decoder throughput.

Windows Ivan offline candidate: cold full synthesis 360.973 ms, warmed approximately 13–22 ms. The candidate is not deployed and does not establish end-to-end latency. First caller-audible confirmation and per-call latency percentiles remain unverified.

**PARTIAL / BLOCKED.** Three real SIP attempts finished, but the booking release gate did not pass. Registration, call establishment and response packets are separate from caller-heard confirmation. Known locale was selected through the existing authenticated call-language control; no STT transcript was injected. Synthetic WAV callers were used, not representative human callers. Raw live transcripts remain disabled by the existing privacy settings.

| Locale | Attempt | Call ID | Last booking state | New confirmed bookings | Request/name/confirm observation ms |
|---|---|---|---|---|---|
| bg-BG | 20261009T100552Z-92117b | 7231118e-9424-4daa-a87a-3e3a46279cc4 | awaiting_confirmation | 0 | 33484/44953/68437 |
| en-US | 20261009T100926Z-58c039 | 1b8ef3fe-c435-46ec-94a3-a6b57cd11df5 | awaiting_confirmation | 0 | 26110/30734/73907 |
| bg-BG | 20261009T101251Z-931cd0 | 099194ab-20ff-44b1-90fd-a5afa9b292d6 | awaiting_confirmation | 0 | 29609/41047/68281 |

Each attempt retains its input hashes, received WAV, redacted signaling, resource samples, conversation, agent handoffs and tool results under artifacts/phase8/sip-tests/<attempt>/. The summary is artifacts/phase8/three-call-results.json. State observation timings include input playback, buffering, inference and polling; they are not synchronized first-audible latency. No new correct booking or three-call success is inferred. The prior correct English booking remains historical evidence, not a Phase 8 pass.

Required remaining gates: reliable telephone-band time/consent recognition, caller-heard intelligibility, real in-call language switching/unavailable/interruption/failure scenarios, visual dashboard verification and three consecutive complete correct bookings. Existing unit tests do not establish those live gates. Browser security policy rejected local dashboard inspection; no indirect or alternate-browser bypass was attempted.

Final backend-lifetime operational snapshot (not per-call percentiles):

| Stage | Count | Mean ms | Max ms |
|---|---|---|---|
| stt_provider | 9 | 6134.90 | 8694.14 |
| tts_provider | 12 | 12243.06 | 16890.06 |
| voice_turn | 9 | 15769.22 | 33493.88 |
| utterance_to_ack_first_packet | 9 | 6101.93 | 6103.14 |
| utterance_final_to_first_output_packet | 9 | 34007.62 | 51838.18 |
| rtp_ingestion | 30097 | 0.11 | 9.07 |

Three call timeout/error events were recorded. Cached acknowledgement delivery averaged about 6.10 seconds; business output averaged about 34.01 seconds after finalized audio. Neither is a guaranteed SLA. Evidence: artifacts/phase8/cleanup-operations.json. RTP ingestion stayed separate from inference.

## Phase 8B measured update — 9 October 2026

STT matrix HTTP-free local inference ranged 4771.84–8399.22 ms across twenty-seven narrowband trials. Actual VAD endpoint is 1800 ms after last active frame, plus the worker settling window; it is not included in offline inference wall time. All nine synthetic VAD replays emitted once. No global resampling/beam change was applied because quality tradeoffs were measured.

Ivan batch/CPU/working-set measurements are in WINDOWS_IVAN_EVALUATION; this candidate is not the response TTS. Trace durations distinguish STT, literal confirmation processing, agent/native tool proposal, existing tool execution, TTS and final-utterance-to-first-output packet. First synchronized human-audible response remains unmeasured. Each call retains its actual Operations snapshot and resource samples; no percentile or whole-host peak is fabricated.

**PARTIAL / BLOCKED.** Deterministic confirmation is recovered; complete live acceptance is not inferred. The owner declared availability for live acceptance before new SIP attempts. Caller fixtures combine existing BG38 speech and authorized Ivan evaluation speech; the assistant's response provider remains BG38. Known locale is selected through the existing authenticated control, without transcript injection.

| Locale | Attempt | Call ID | Business workflow | Booking IDs | Human-heard verification |
|---|---|---|---|---|---|
| bg-BG | 20261009T105422Z-29fa08 | 38d1e640-f178-4b59-a901-021bbd8103e8 | True | e1918d21-a585-4b07-85dc-2947b037c450 | pending |
| en-US | 20261009T105839Z-e5d106 | 8c3cb1f5-ab9e-4853-890a-6180ed1a0e11 | True | 4c04be6e-27f1-4925-9737-3f6c7ff79a91 | pending |
| bg-BG | 20261009T110159Z-7f0d1a | 33c8e022-7c76-4ad2-a4c6-765caebd2c62 | True | f170806c-a94b-4c58-9379-cae95c27e9e2 | pending |

Three consecutive complete calls, human-audible correct confirmation, visual dashboard evidence and the acoustic question false-positive control remain open gates. Received RTP/nonzero WAV/persisted row alone cannot satisfy human acceptance. New receipts are artifacts/phase8b/sip-tests/<attempt>/; prior unsuccessful attempts remain in Phase 8 evidence. Sequence continuation is permitted only after the preceding business journey passes; no failure is silently omitted. Browser policy previously blocked local inspection and is not bypassed; the owner can verify the dashboard directly.

All three consecutive selected-affirmative SIP business journeys passed. Each created one distinct correct appointment, and response audio reached the caller transport. All three survived the targeted backend restart; no active API calls or Asterisk channels remain. Caller-side final-45-second excerpts were provided for human listening. This is business/transport evidence, not full human acceptance.

The owner initially reported ERR_CONNECTION_REFUSED when checking the dashboard. The intended URL is http://127.0.0.1:3011/dashboard; the existing listener was verified on 127.0.0.1:3011 and returned HTTP 200. Visual booking verification remains pending the owner’s follow-up; HTTP availability is not visual proof.

Call 38d1e640-f178-4b59-a901-021bbd8103e8, correlation 75c3655015918973c0cc014e4f31b4ef:

| Stage | Observed duration ms |
|---|---|
| stt_final | 6351.217 |
| confirmation_evaluated | 0.922 |
| tts_completed | 8019.241 |
| output_packet_sent | 19522.417 |
First outbound packet is caller-transport delivery, not a synchronized human-audible measurement. State observation timing remains separate.

Call 8c3cb1f5-ab9e-4853-890a-6180ed1a0e11, correlation 35a5bc61406158df55050cb5b552b2d4:

| Stage | Observed duration ms |
|---|---|
| stt_final | 6600.605 |
| confirmation_evaluated | 0.301 |
| tts_completed | 6962.831 |
| output_packet_sent | 23881.862 |
First outbound packet is caller-transport delivery, not a synchronized human-audible measurement. State observation timing remains separate.

Call 33c8e022-7c76-4ad2-a4c6-765caebd2c62, correlation fc22b06009621e793a3763f11829c568:

| Stage | Observed duration ms |
|---|---|
| stt_final | 9566.942 |
| confirmation_evaluated | 0.712 |
| tts_completed | 8778.144 |
| output_packet_sent | 26652.287 |
First outbound packet is caller-transport delivery, not a synchronized human-audible measurement. State observation timing remains separate.

Measured owned-container lifetime cgroup peaks (includes startup/cache/kernel; different lifetimes, not a simultaneous aggregate or per-call RSS):

| Service | Charged peak bytes | Automatic restart count | OOM killed |
|---|---|---|---|
| qwen | 4294967296 | 0 | False |
| stt | 738668544 | 0 | False |
| tts | 1921519616 | 0 | False |
| backend | 101912576 | 0 | False |
| asterisk | 154800128 | 0 | False |
| frontend | 25542656 | 0 | False |

Qwen reached its 4 GiB cap; no OOM kill or automatic restart was observed. STT was deliberately stopped/restored for offline evaluation; backend was deliberately recreated for the targeted fixes. CPU cumulative/throttle counters are retained in cgroup-memory-final.json; per-call actual CPU/memory samples remain in resources.json. Independent regression/build tasks ran during portions of development; these measurements are not isolated capacity guarantees.
