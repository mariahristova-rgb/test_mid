# Performance baseline and results — 10 October 2026

These are actual source/build and localhost HTTP measurements, not browser LCP/INP/CLS or mobile results. Browser inspection remains blocked. CPU contention and loopback transport limit generalization.

## Loader budget

Phase 12 started with no widget, so the host-page widget baseline was zero bytes. The new loader budget is at most 4096 gzip bytes, enforced by a Node source test. No speech models or large SDKs load on the host. The iframe is lazy; loader CSS is isolated in Shadow DOM. Gzip sizes below are measured source estimates. Actual nginx wire gzip and decompressed equality with the source loader passed in artifacts/phase12-http-security.json.

| Asset | Raw bytes | Gzip bytes |
|---|---:|---:|
| catalog.js | 3029 | 1345 |
| frame.css | 1226 | 652 |
| frame.html | 1779 | 801 |
| frame.js | 6814 | 2384 |
| loader.css | 746 | 428 |
| v1.js | 4568 | 1747 |

## HTTP samples

Sequential localhost urllib HTTP, 20 samples per GET; no mobile/throttling/browser engine.

| GET | Samples | p50 ms | p95 ms |
|---|---:|---:|---:|
| loader | 20 | 19.97 | 30.22 |
| iframe | 20 | 18.75 | 30.95 |
| sample_site | 20 | 12.12 | 14.07 |

Six real widget POST turns through mock agents/calendar measured 199.77–339.37 ms, median 254.05 ms. This includes two persisted confirmed bookings; it is not Qwen token latency or production capacity.

Final dashboard assets total 305952 bytes. Build entry JS: 197.06 kB / 68.56 kB gzip; WidgetView is a separate lazy 9.62 kB chunk. The earlier Phase 11 entry was 186.68 kB, so bilingual widget resources increased the dashboard entry by 10.38 kB. No universal speed improvement is claimed.

Asset responses use five-minute cache headers and content-digest ETags; the server does not currently implement conditional 304 handling. JSON session responses remain uncached. No streaming provider is certified, so responses are complete-message HTTP.

Targets awaiting actual desktop/mobile and slow-network measurement: LCP ≤2.5 s, INP ≤200 ms, CLS ≤0.1 at p75; bootstrap/time-to-interactive/first-response/retry/error metrics need browser instrumentation. Server request timing and persistent admission/session/message counts provide preliminary diagnostics, not end-user field measurements.

Evidence: artifacts/phase12-performance.json; artifacts/phase12-journey-state.json; artifacts/phase12-final-frontend-build.txt.
