# Architecture and cost decision

Checkpoint 11 October 2026. Keep the existing single-process modular monolith for bounded synthetic staging. Website/static widget, public session routes and protected staff routes are isolated by proxy and capabilities; agent/scheduler execution still shares one backend process. These are logical boundaries, not independently durable worker services.

Options: existing static website hosting has no new implementation spend but cannot run FastAPI; temporary e2-micro staging already exists and has a historical €1.9577/week estimate including disk/IP/contingency; Cloud Run with external durable storage would require a new database/queue and pricing review; a persistent Qwen/voice host requires actual capacity benchmarks and separately approved budget. No unverified current price or free-tier guarantee is asserted. No new provider selected or resource created.

SQLite schema 5 and transactionally claimed local jobs are not HA. Before replicas: PostgreSQL adapter, durable queue, cross-process locks/idempotency, safe migration and tested restoration. Do not use local-volume SQLite across replicas. Kubernetes is unnecessary for this bounded topology.

Preserve local persistent Qwen cache and original GCS artifacts. Staging e2-micro does not serve inference, STT, TTS or SIP. New inference sizing must use warm/cold throughput, peak RAM and concurrency measurements; existing CPU reports cannot certify this cloud host.
