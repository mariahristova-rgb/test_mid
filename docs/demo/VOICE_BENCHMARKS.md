# Voice benchmarks — no live measurements yet

No actual Qwen, STT, TTS, SIP or caller-audible latency was measured. Synthetic contract timings are excluded from this benchmark. Targets are under 1.5 seconds for first audible simple replies and preferably under 2.5 seconds for ordinary turns; these remain targets.

| Stage | Instrumentation | Actual live result |
|---|---|---|
| RTP ingestion | Content-free `rtp_ingestion` span | NOT_MEASURED |
| VAD/end of speech | Existing energy buffer, configured turn silence | NOT_MEASURED |
| STT | `stt_provider` span | NOT_MEASURED |
| LLM | Inference receipts: elapsed, reported tokens; first visible token for explicit SSE | NOT_MEASURED |
| Agents/tools | Existing agent/tool spans | NOT_MEASURED |
| TTS | `tts_provider` span; batch output currently | NOT_MEASURED |
| Utterance final → first output packet | New voice runtime span | NOT_MEASURED |
| Last caller audio → first audible reply | External softphone measurement needed | NOT_MEASURED |
| Queue/sessions | Tenant-scoped current depth/session gauges | NOT_MEASURED with live calls |
| CPU/RAM/GPU/VRAM | Target host/container monitoring required | NOT_MEASURED for inference |

First output packet is a transport metric, not proof of first audible playback. VAD silence, network delay, TTS batching and softphone jitter add latency. Non-streaming agent inference is used in the integrated booking workflow; the standalone SSE contract does not imply streaming speech.

Implemented low-cost measures: initialization-only model cache, persistent local speech engines, one shared owner Qwen serving process, output limit 256, no redundant free-text LLM call before intent extraction, bounded audio/worker queues and playback cancellation. Remaining optimization gates: real warm-up and GPU/resource measurements, native speech timeout isolation, streaming synthesis, acknowledgment during long operations, echo/noise VAD testing and SQLite transaction contention during model calls. Do not change correctness/confirmation boundaries merely to improve timings.
