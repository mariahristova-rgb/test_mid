# Information, business and feature workflows

Typed ConciergeRequest is delegated by the existing Receptionist/Task Execution agents and ToolRegistry, with tenant/session permissions, locale, correlation and idempotency. Requests persist in tenant-owned operations records; owner reads them through the private /api/concierge/requests endpoint.

Information collects name, verified email, topic/language and optional company; sends only approved public Ontelyx links. Business inquiry collects name/company, needs/topic, email and timeline; optional contact email is validated but not falsely described as verified. It notifies only the server-configured business inbox. Features capture proposal/topic and use-case/impact, with optional name/email. Both persist and acknowledge received/notification queued, never delivered before Google confirms sending.

Explicit request consent is required. Marketing consent is a distinct optional false-by-default choice; no automatic marketing subscription exists. There are no upload/attachment fields or confidential invention materials. Public knowledge comes from approved website marketing text and config/ontelyx_concierge.json; uncertain questions offer a business inquiry/demo.

Session quotas, persistent tenant/integration limits, proof attempt limits and generic request rate limits provide preliminary abuse protection. Public edge CAPTCHA/abuse review remains a staging gate; Origin is not identity. Customer-submitted business data is a separate retained business record, not erased by chat clear. Full business-record deletion/retention/export policy and Google mailbox retention need operator review before production.

Request retention is configurable (default 30 days, not above tenant policy). Bounded cleanup redacts expired request fields and matching tool/handoff copies, cancels stale queued notifications and clears encrypted email-body copies when not already sending/uncertain. Separately retained bookings, Google mail and backups still require the documented business privacy procedure.
