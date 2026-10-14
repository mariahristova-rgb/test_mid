# Phase15 baseline results

11 October2026. Local Windows/Docker; no representative mobile network simulation. Baseline test_mid4ddf9ee, ontelyx40894dc. Fresh backend296 tests/97.135s; frontend22 tests plus lint/typecheck/build. Previous verified website78 tests and build/typecheck/format/config checks were rerun immediately before Phase15; no Phase15 website runtime change yet.

Read-only phase14_local_check.py sampled20 sequential loopback GETs: website p50=29.55ms/p95=34.14ms; loader14.35/27.77ms; admin7.41/24.44ms. Actual website entry139200bytes, Python gzip52226; loader5710/2128gzip. This is HTTP/body size, not rendering or LCP/INP/CLS.

Frontend baseline build: entry200.98kB/69.91kB Vite gzip; Workspace53.10/13.31; CSS13.75/4.07. Compiler's kB estimates and Python byte compression are different methods and not combined as one series. No task-time participants, p75 field dataset, CPU/heap/mobile memory or long-task results exist.

Qwen/STT/TTS/Asterisk CPU stack is unchanged. Its prior measured failures/voice limitations remain in docs/demo/VOICE_LATENCY_RESULTS.md; they are historical, not fresh Phase15 benchmarks. No speculative model/hardware tuning was performed. scripts/benchmark_phase11.py provides disposable-store SQL/API measurement; its older results are not asserted as this run.
