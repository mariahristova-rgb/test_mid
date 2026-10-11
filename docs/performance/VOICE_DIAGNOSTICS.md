# Voice diagnostics and resource scope

10 October 2026. Existing Qwen3-4B Q4_K_M, faster-whisper small CPU/int8, BG38/MioCodec, Asterisk/SIP, persistent model volumes and one-call CPU limits remain. No inference image, model, voice, provider credential, recording policy or confirmation mode was switched by the UX work.

Actual idle Docker snapshot before local update: frontend 16.21 MiB (0% CPU), backend 70.11 MiB (0.32%), Asterisk 71.69 MiB (1.88%), TTS 1.343 GiB (0.39%), STT 603.9 MiB (0.34%), Qwen 2.544 GiB (0.01%). These are instantaneous container observations, not peak RAM or capacity guarantees. Host is the previously audited 16 GB Windows/integrated-graphics CPU environment; no CUDA assumption is added. No WSL limit change or duplicate inference service was made.

Debugger exposes only actual content-free voice trace entries: audio/VAD/STT/locale/pending/confirmation/agent/tool/appointment/TTS/first output packet/close where recorded. Trace storage is bounded process memory (256 entries per tenant); restart may remove it. Monotonic times are not wall-clock timestamps. Duration is shown only when measured. Missing and not-applicable coverage are explicit. Metadata may survive while private transcripts remain omitted.

No new SIP booking call, warm/cold model benchmark, audio recording or peak-memory run was performed for Phase 11. Prior failures remain in docs/demo/PHASE9_READINESS.md and PHASE9_SAFETY_PREPARATION.md. Audio sent is not proof of caller hearing, Bulgarian intelligibility, safe consent recognition or PSTN connectivity. Voice acceptance remains DEMO_BLOCKED independently of UX changes.

Next: resolve consent/date speech failures, obtain authorized BG/EN listening and dashboard evidence, then perform the separate attended three-call acceptance. This UX phase cannot waive that gate.
