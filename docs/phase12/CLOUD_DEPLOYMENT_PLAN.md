# Portable staging plan — no resources provisioned

Retain Windows Docker/WSL2 as development/demo. The Phase 12 local overlay adds two limited-memory nginx services and exposes only loopback ports. Qwen/STT/TTS/Asterisk images, caches and endpoints remain unchanged. Do not deploy this demo overlay publicly.

| Boundary | Minimum staging responsibility | Scaling requirement |
|---|---|---|
| Customer sites / static loader | Versioned assets, HTTPS, cache/compression, measured browser acceptance | CDN with reviewed origin policy; no secrets |
| Widget origin | Only widget routes, restrictive CSP/CORS, admission abuse controls | Separate HTTPS ingress; never staff/model/SIP routes |
| Authenticated app/API | Verified identity, RBAC, encryption, tenant ownership | Existing single-process SQLite initially; no multiple independent writers |
| Orchestration / tools | Snapshot/consent enforcement, bounded workers | Shared transactional DB, distributed quotas/idempotency and durable queue before replicas |
| Qwen inference | Private network, authenticated endpoint, persistent authorized model cache | Independent resource and concurrency limits |
| STT / TTS | Private warm workers, verified BG/EN speech and licenses | Separate CPU/memory budgets; browser voice stays off |
| Data / backups / objects | Encryption, retention, tested restore, tenant boundaries | PostgreSQL/object-storage migration requires separate implementation/tests |
| Observability | Redacted request latency/error/usage, admission counts | Central logs, alerting and tested incident/abuse procedures |
| SIP / Asterisk | Separately approved verified telephone runtime | Long-lived RTP/ARI transport on suitable VM/container hosts; not request-timeout functions |

`semantic_os/deploy/widget.staging.env.example` contains file paths and secret references, no secret values. Existing production compose is a foundation, not a certified widget deployment. Production ignores local nonce-fetch target mappings. Confirm distinct HTTPS app/widget origins, managed identity/JWKS, private ingress to model workers, restrictive egress, backups and deletion before staging.

Cost categories: compute/memory for app and inference, storage/backups/cache, CDN/bandwidth, logs/metrics, database/queue and optional approved telephone connectivity. No prices or paid provider commitments are assumed. Start with one app writer and one isolated text demo session; observe resource use before sizing. Do not purchase domains, expose services, create cloud resources, migrate business records or enable real messages/payments without separate approval.

Open gates: verified public registration, real LLM/calendar promotion, browser/mobile/accessibility/security review, edge abuse control, distributed data model, telemetry/alerts, restore and complete business-data erasure. Telephone acceptance remains blocked independently.
