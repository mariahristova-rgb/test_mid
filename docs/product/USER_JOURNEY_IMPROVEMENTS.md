# User journeys and first value

11 October 2026. Local feature branch `codex/phase15-product-experience`; no Phase 15 push/merge/public deployment. Existing URLs and the two-agent runtime are retained.


Existing Configure → Connect → Test → Review → Publish flow remains in SetupView.vue and ux.py. Saved drafts and immutable receipts are reused; generic receptionist/support/sales use cases exist. Industry presets are P2, not yet implemented.

Observed blocker: demo re-login previously reset the organization during OAuth, repeatedly connecting SmileCare instead of Concierge. Phase14 tenant-specific settings links and bootstrap validation resolve this without transferring credentials across tenants. Current Google accounts are connected and operations remain off outside approved test windows.

Phase15 increment: grouped navigation, collapsible advanced experiences that open for their current route, tenant-owned queue state/revision and audited staff notes. Queue classification does not pause/resume AI; existing human controls retain that responsibility. Notes never create external messages. Unknown queue state is displayed as Not classified rather than falsely needing review.

Proposed top-task paths: Business → Conversations → queue/takeover; Assistants → existing draft → tests; Operations → Google settings. These are design interaction counts, not timed participant metrics. No under-five-minute onboarding result is claimed.

Open: screen-reader/mobile journey, Leads & Requests presentation, explicit conflict refresh guidance, full publishing/unpublishing browser acceptance. Browser inspection attempt was rejected; no alternate CDP/screenshot helper was used.
