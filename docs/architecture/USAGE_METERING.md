# Usage metering and entitlements

Billing usage is append-only at both service and database-trigger layers. Every event contains tenant/resource, category, integer quantity, unit, provider, aware timestamp, correlation, idempotency key and UTC YYYY-MM billing period. Fingerprints reject reuse of a key with different event data. Plan/version/rate snapshots and integer charge_minor are retained. No floating-point billing totals are used.

| Category | Measurement |
|---|---|
| AI messages / agents / tools | Accepted mock action units, transactionally reserved before execution; duplicate events/actions reuse results |
| Voice | Observed call seconds, rounded upward to an integer; active calls reserve available admission budgets and timers use those budgets |
| STT | Real PCM input seconds when supplied; synthetic UTF-8 transcripts have no invented speech duration |
| TTS | Requested text characters per synthesis attempt; nonbillable until reconciled with actual provider usage |
| SMS | GSM-7/UTF-16 segment calculation; accepted outbound messages are metered once |
| WhatsApp / email | Accepted outbound message units; distinct drafts are not charged as delivered messages |
| LLM input/output tokens | Schema and limit/report support exist; the mock does not report actual token counts, and unknown values do not create fabricated charges |
| Storage | Current encrypted-secret/media byte allocation is a gauge; creation/growth checks actual ciphertext size |

Usage month is UTC and independent of tenant UI timezone or annual subscription interval. UI converts dates using the explicit tenant timezone. Resource allocations count active resources; monthly counters count recorded activity. Quotas/warnings apply to mock activity as well, while mock billing remains nonbillable.

Outbound dispatch claims reserve allowance before leaving the database transaction. Explicit provider rejection releases the reservation for safe backoff. Timeouts/unknown acceptance retain it. Meter records use a persistent message identity, so an early callback and successful dispatcher completion cannot charge twice. Verified sent/delivered/read callbacks settle an unknown send. Operator reconciliation totals are review records, not permission to blindly resend an irreversible action.

`GET /api/usage` exposes actual/held quantities, limits, warning policy, month and unknown-token status. `POST /api/billing/usage-report` accepts only authorized mock nonbillable reports. Trusted live provider usage ingestion and vendor pricing remain unverified integrations. Real reported charges must be reconciled before commercial collection.

History retention cannot exceed the subscription cap. Voice timer granularity and unverified carrier termination can overrun an admission estimate; observed consumption is retained rather than discarded, and later requests are blocked by remaining allowance. The current single-process topology and external provider limits are not an SLA or production concurrency guarantee.
