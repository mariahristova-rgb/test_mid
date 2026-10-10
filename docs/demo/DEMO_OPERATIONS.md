# Demo operations — Phase 8

Reuse the existing scoped project testmid-cpu-voice and scripts/demo/start-local.ps1 -NeuralVoice, stop-local.ps1, check-local.ps1 and reset-demo.ps1. Startup uses verified existing caches/model volume; no GCS download occurs during calls. Reset requires the marked synthetic tenant and idle/stopped services, archives data and preserves audit evidence. Do not apply it to production.

Phase 8 began with Docker Desktop stopped. The installed CLI docker desktop start restored the runtime; only existing scoped images were started. Unrelated cruise containers are not altered. Backend image changes package only targeted audio/consent fixes; the agent/framework/inference infrastructure is preserved.

Commands used: scripts/phase8_audio_audit.py (600/1200/1800 ms comparisons); scripts/phase8_speech_corpus.py inside the owned backend; scripts/phase8_windows_voice_eval.ps1 through Windows PowerShell for offline installed-voice evaluation; scripts/phase8_windows_stt_check.py inside STT; scripts/benchmark_cpu_llm.py --compact; backend unittest discovery; frontend typecheck/lint/test/build.

Current demo endpoint window is 1800 ms, max one call, locale choices bg-BG/en-US. Unclear confirmation re-prompts rather than cancelling solely on a model guess. Do not approve mismatched proposals. No corrupted name/date/consent is rewritten into a successful result.

Web Chat fallback uses the same Qwen agents, permission-controlled tools and persistent calendar path through the existing dashboard conversation UI. Label it Web Chat fallback; it is not a live phone call. Visual browser verification remains pending due the earlier policy block.

Major TTS replacement is inactive while awaiting the owner's Phase 8 approval. Installed Ivan/English voice assets remain in Windows; they are not redistributed or copied into Docker. Any approved bridge must be authenticated, privately bound, preserve the adapter contract and retain production licensing review as a separate gate.

## Phase 8 measured outcome — 9 October 2026

Three actual calls completed with zero active API call sessions (0) and zero Asterisk active channels/calls. The Asterisk diagnostic recorded three calls processed. Caller processes exited normally. Existing persisted bookings remain; these Phase 8 attempts created none. Evidence: artifacts/phase8/cleanup-operations.json and three per-call result files.

All required reports now preserve the measured failures and open gates. Service health, zero active channels and passing regressions do not establish demo readiness. Existing services are retained for owner review; no unrelated container was stopped. The major TTS replacement remains pending explicit Phase 8 approval.
