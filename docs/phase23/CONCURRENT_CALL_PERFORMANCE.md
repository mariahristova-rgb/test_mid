# Concurrent-call performance

Actual single/two/higher-call latency,peak RAM/VRAM,queue/buffer contention and demonstrated capacity: **NOT TESTED in Phase23**. Existing configured one-slot Qwen/native speech workers and bounded voice-session controls are not multi-call performance evidence. Fresh73tests use mocks,not simultaneous real model calls.

Plan after approval: one synthetic session with exact pinned models/reference/audio; warm/cold stages,EOF→first audio,ASR/LLM/TTS/tool durations,CPU/RAM and failed/cancelled sessions. Proceed to two only after memory/quality headroom and explicit run scope; verify tenant buffers,backpressure,timeout/overload,no double tool writes and graceful termination. Record exact sample size/errors and configuration. No higher capacity promise from one successful call.

Dated Phase21audit:15.35GiBtotal/2.86GiBfree,Docker7.44GiB,integrated GPU; not a fresh load baseline. No resource allocation,replica,WSL change,paidGPU or new model started. Hardware expansion requires measured deficiency and independent budget/topology approval; SQLite/locks remain one process.
