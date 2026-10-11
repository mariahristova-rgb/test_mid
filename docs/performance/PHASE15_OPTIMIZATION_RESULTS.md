# Phase15 optimization results

No performance optimization is claimed. The measured first increment adds navigation grouping and Inbox UI: entry203.21kB/70.73gzip versus200.98/69.91 baseline; Workspace55.68/13.96 versus53.10/13.31. Added capability increases transfer. Latest final CSS/build should be consulted after formatting; no field-vitals delta is inferred.

Queue updates use the existing SQLite transaction/revision check and operations_events; no schema migration or additional analytics DB. Notes capped100 per conversation,2000chars; purge bounded500 records per maintenance run. Read plans/polling and small widget loader remain unchanged. Audit queries still require tenant scope and RBAC.

Web LCP/INP/CLS, widget-open latency, UI hydration, slow network, heap, long lists, Google FreeBusy p50/p95, inference first token, STT/TTS/RTP and participant first-value time are UNMEASURED for Phase15. Goals remain goals. Browser inspection rejected by auto-review; do not substitute API latency for UX metrics. Optimize only after representative before/after evidence.


## Executed API profile

Existing benchmark_phase11.py, disposable ASGI/SQLite memory store, 1000 synthetic conversations, concurrency1, 20 sequential samples per endpoint. Same host, baseline4ddf9ee versus local feature source. Values are milliseconds; not browser/network/provider latency. No optimization was applied and deltas include run variance.

| Endpoint | Before p50 / p95 | After p50 / p95 |
|---|---|---|
| assistants | 12.651 / 16.6708 | 10.5796 / 12.3275 |
| conversation_list | 46.3565 / 67.2814 | 49.0428 / 59.8358 |
| conversation_detail | 9.4729 / 15.7029 | 15.5642 / 19.8319 |
| call_activity | 10.314 / 12.2074 | 13.6753 / 17.3846 |
| operations | 10.2224 / 13.7303 | 11.5551 / 16.5632 |
| conversation_page | 14.4676 / 16.6733 | 18.0358 / 29.8612 |
| booking_three_turns_direct | 15.3657 / 33.3484 | 31.268 / 51.6818 |
| booking_three_turns_http | 63.3149 / 78.2993 | 80.4428 / 104.2197 |
| isolated_test_execution | 15.3862 / 24.1183 | 25.6214 / 33.9408 |

Evidence: artifacts/phase15/api-before.json and api-after.json include query plans/statement counts. No p75 UX or inference performance conclusion follows.


## Local browser observations

Opt-in official web-vitals dependency is lazy in local demo builds and excluded by the explicit production flag. No external telemetry, raw URL, transcript or attribution data is recorded. Initial desktop login/Inbox session1280x720: LCP1412ms,CLS0,INP480ms. Second390px initial session followed by mixed resizing/keyboard interactions: LCP1832ms,CLS0,INP992ms. These are single synthetic sessions on unthrottled local Windows Chromium, with concurrent Docker work; not matched p75 or representative mobile networking. INP target is not met in these observations. No speculative optimization or performance-ready claim.
