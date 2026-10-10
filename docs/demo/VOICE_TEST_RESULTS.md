# Phase 6C verification record — 2026-10-08

The pre-change backend regression suite passed 168 tests. Nine new offline Qwen/artifact contract tests cover checksum/path validation, cache reuse/tampering, license gating, explicit backend selection, Bulgarian text/non-thinking payload, reported/missing usage, reasoning fragments, cancellation/context/public-HTTP rejection, tool rejection and SSE fragments.

The first sandbox test run encountered Windows temporary-directory access errors. The complete suite then passed **177 tests in 45.070 seconds** outside that restriction. The source/import/syntax boundary check passed **106 files, zero failures**. The deployment sync CLI help check passed. Frontend code was unchanged and its earlier Phase 5 results were not rerun in this increment.

These tests use httpx synthetic responses and tiny synthetic GGUF-marker files, not real model weights. No actual Qwen generation, STT/TTS audio, SIP registration, call, appointment-through-SIP or dashboard call result was measured. Time-to-first-token and end-to-end latency are unmeasured; the under-two-second goal remains unverified. Tenant isolation for the existing application remains covered by its baseline suite; new live routing isolation is pending implementation.
