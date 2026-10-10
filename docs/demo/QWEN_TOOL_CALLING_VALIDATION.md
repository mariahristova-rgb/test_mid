# Qwen tool-calling validation — Phase 8

Existing Qwen3-4B Q4_K_M is reused; no GCS reload/download or model upgrade occurs during calls. Derived artifact SHA-256: 9a91506f18e56bfa9389a939db1b36029daf8c49327b0eb0bc9e19d627b00e79. Original revision/tokenizer provenance remains in MODEL_MEMORY_REPORT. Serving uses pinned llama.cpp, context 4096, four CPU threads, one parallel slot, GPU layers zero, Jinja template and non-thinking mode. Output caps remain bounded; endpoint timeout is configured independently of the 90-second turn budget.

Actual Phase 8 compact probes passed Bulgarian/English booking intent, preserved 15:00/default duration, and returned native CheckAvailability tool JSON bound to exact request-scoped validated arguments. No business tool is executed by this benchmark. Latest timestamped evidence: artifacts/local-demo/llm-benchmark-compact-*.json.

Observed BG greeting: first visible token 17,735.45 ms, total 20,065.52 ms, 0.349 reported completion tokens over request seconds. EN: 5,314.64 / 8,403.25 ms, 1.190. These are whole-request metrics, not native decoder-only speed. The 2-second/4-second goals are aspirational and unmet in these measurements.

New regression: a model-only cancel guess for corrupted confirmation cannot discard the pending proposal. Only explicit caller cancellation phrases cancel it. Required “Да, потвърждавам резервацията” is accepted; negatives, questions and corrupted spellings remain rejected. Existing permission/schema/idempotency/cancellation tests remain mandatory. No hallucinated booking success is accepted before tool persistence.
