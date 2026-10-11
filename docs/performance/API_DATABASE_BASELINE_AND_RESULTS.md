# API and database benchmark

10 October 2026. Controlled in-process FastAPI/ASGI TestClient, in-memory SQLite, 1000 synthetic conversations, one concurrent request, 40 measured samples per case after warm-up. Before source 213e0ce was exported inside ignored artifacts; matched runs were sequential. No live database/provider was used. Rate-limit budgets are raised only inside this benchmark process. p99 with 40 samples is the maximum nearest-rank sample, not a reliable production-tail estimate.

| Workload | Samples | Before p50 / p95 / p99 ms | After p50 / p95 / p99 ms |
|---|---|---|---|
| assistants | 40 | 9.6184 / 10.6959 / 12.0719 | 10.3223 / 13.3912 / 13.8006 |
| conversation_list | 40 | 46.7396 / 84.5885 / 89.9176 | 53.6022 / 95.3914 / 223.926 |
| conversation_detail | 40 | 11.0234 / 16.1074 / 16.759 | 7.8728 / 9.673 / 9.7528 |
| call_activity | 40 | 11.3296 / 15.0044 / 17.5853 | 8.4796 / 10.4992 / 10.7609 |
| operations | 40 | 10.0386 / 12.4553 / 12.7548 | 8.8297 / 10.1421 / 10.5003 |
| booking_three_turns_direct | 40 | 35.2447 / 52.2017 / 56.4212 | 23.5596 / 40.4502 / 46.4773 |
| booking_three_turns_http | 40 | 107.1226 / 150.1865 / 162.5148 | 104.0978 / 158.4821 / 178.4519 |

- conversation_page: {"samples": 40, "p50_ms": 15.9213, "p95_ms": 24.5884, "p99_ms": 27.577, "response_bytes": 10511}
- isolated_test_execution: {"samples": 40, "p50_ms": 26.1503, "p95_ms": 60.8707, "p99_ms": 80.1189}

Full inbox read statements: 1005 before, 4 after, including authentication reads. The inbox data itself now uses one SQL statement with tenant-scoped message/contact joins. Legacy unbounded shape and ascending order are preserved; new pages apply filters before cursor/limit. Equal timestamp ties use reception order and mixed timezone offsets compare actual instants. Dates are filtered in the tenant timezone with an exclusive next-day boundary.

Full payload is 207230 bytes versus 10511 bytes for a 50-row page. Smaller pages return less data; this is not an identical full-result workload. Full-list timing did not improve in the matched run, and several earlier runs varied materially. No blanket API speedup is claimed. The direct booking metric excludes HTTP; the HTTP metric covers three message requests and successful confirmation. Conversation detail fixture is empty; call activity fixture has no business execution history.

Query plans are retained in both JSON receipts. Tenant indexes are used; temporary sorting remains. No new index, migration, connection pool, reduced tenant checks or changed ledger rules were introduced. The measured N+1 request pattern justified the query rewrite and bounded paging, not speculative database tuning.

Reproduce: .venv/Scripts/python.exe scripts/benchmark_phase11.py --source-root artifacts/phase11-baseline-source --output artifacts/phase11-api-before-matched.json; then the same command without --source-root to artifacts/phase11-api-after-matched.json. Windows internal loopback sockets require execution outside the restricted sandbox. Initial sandbox runs stalled in asyncio _fallback_socketpair; that is recorded in phase11-backend-diagnostic.txt, not counted as a pass.

No production-network/SQLite-disk/cold-start/concurrent voice API p95 or p99 is established. New call diagnostics share metadata with the existing activity endpoint but lack a separate representative populated-call latency benchmark. Historical operations are process-local aggregates, not stored percentile distributions.
