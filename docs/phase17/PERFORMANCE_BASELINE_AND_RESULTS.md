# Performance baseline

No fresh network/model/Web Vitals benchmark executed in this increment. Historical Phase16 matched synthetic API data shows mixed results/regressions, not a universal optimization: inbox-page p95 14.9024→20.1293ms; three-turn mock booking p95 63.4688→135.0516ms. Host load was uncontrolled; in-process SQLite/mock timings are not customer latency.

Before optimization collect public mobile/desktop LCP/INP/CLS, gzip bytes, open-to-interactive/session/first response, query plans, provider FreeBusy latency, job lag and failure/unknown rates. Model warm/cold throughput/memory and voice audio latency require separate hosts/scopes. Existing idle staging memory is not peak capacity.

Evaluation runner elapsed_ms measures each synthetic test execution including setup, not API response or model inference latency. No new capacity claim.
