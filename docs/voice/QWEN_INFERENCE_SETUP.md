# Qwen inference adapter — current Phase 7D integration

The earlier standalone limitations below are historical. Qwen is now routed through the existing Receptionist/Task Execution agents, guarded tool registry, call-scoped cancellation and persistent usage ledger. The owner-supplied BF16 source was verified and converted separately to Q4_K_M; CPU loading and real bilingual structured probes were performed. Non-streaming cancellation closes the in-flight client, including header waits. Current serving/deployment and measured failures are documented in docs/demo/CPU_ONLY_CONFIGURATION.md and VOICE_LATENCY_RESULTS.md. This integration does not establish live voice or production readiness.

## Historical Phase 6C contract

`assistant/qwen.py` implements the neutral LLM port against an owner-controlled compatible `/chat/completions` service. The endpoint is a base URL such as the owner's `/v1` URL; none is configured here. Authentication is passed separately as a bearer secret, never embedded in URLs. HTTPS is required except explicitly enabled private IP/localhost HTTP deployments. No registry fallback, conversion or automatic switch to 8B exists.

Default model: Qwen3-4B, output 256 tokens, context budget 4096, timeout 20 seconds. Native structured intents/tool proposals, bounded SSE text, cancellation, non-thinking template hints and visible-output reasoning-tag filtering have offline tests. Byte-based conservative context estimation is used pending a verified tokenizer; the server must enforce its tokenized context limit. Only server-reported token counts are measured. Missing counts are marked unreported. Tool proposals execute nothing and must pass the existing registry authorization/schema/confirmation checks when integrated.

This adapter is **not yet wired into tenant/assistant routing, either agent, the persistent billing ledger or voice barge-in**. Non-streaming cancellation is checked before/after the HTTP call; it does not currently interrupt an in-flight non-streaming request. Serving backend compatibility, model identity and real Bulgarian/native-tool behavior remain unverified. Do not enable it as a live product provider yet.

An existing authenticated endpoint is preferred. Actual existing GGUF can select llama.cpp; HF Safetensors requires a verified compatible GPU/runtime for vLLM. The observed local AMD integrated GPU is not a verified CUDA target. A valid artifact manifest is required before backend selection, memory sizing or latency claims.
