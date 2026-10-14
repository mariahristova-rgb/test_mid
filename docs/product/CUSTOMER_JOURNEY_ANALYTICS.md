# Outcome and funnel definitions — proposal

11 October 2026. Local feature branch `codex/phase15-product-experience`; no Phase 15 push/merge/public deployment. Existing URLs and the two-agent runtime are retained.


Current dashboard is persisted counts, not verified conversion. A separate analytics store is not justified. P1 will project metadata from conversations, agent/tool executions, operations_events, appointments and jobs; raw message/email bodies must not enter analytics.

Definitions: completed booking requires provider-confirmed creation and persisted appointment; cancelled booking is a separate outcome, never a completed-current booking. Failed booking requires recorded error; abandonment cannot be inferred from a short/empty conversation alone. Inquiries require concierge_request records. Response latency requires observed monotonic/wall-clock matching pairs and a sample count, not a fabricated zero.

Funnel: widget opened (not recorded reliably; unknown) → redeemed session/conversation started (widget session record) → intent identified (actual handoff/action) → availability offered (successful tool result) → confirmed (explicit approval/proof) → calendar persisted (verified event/appointment). These stages must not imply one-to-one monotonic conversion when sessions retry or skip a stage. Show date/channel/locale/assistant filters, tenant timezone, numerator/denominator and missing coverage.

NOT_IMPLEMENTED: new dashboard/report/funnel and quality ranking, pending P0 acceptance. Existing two approved live tests are acceptance traffic, not customer conversion KPIs. No marketing subscription, new telemetry vendor or transcript retention is introduced.
