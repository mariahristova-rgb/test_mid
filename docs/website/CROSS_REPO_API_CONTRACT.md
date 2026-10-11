# Concierge v1 release contract

Backend owns authorization/business state. Website owns presentation, public origin/ID and mobile lifecycle. Both use the same loader/iframe; website src/assistant-contract.ts describes public receipts/capabilities, never Google credentials. Versioned capability response schema_version is 1.0.

| Route | Authority / behavior |
|---|---|
| /widget/admission/{public_id}, redeem | Existing verified-origin one-use ticket and scoped session |
| GET /widget/v1/concierge/{public_id} | Visitor bearer; sanitized policy/capabilities; voice false |
| POST /widget/v1/actions/{public_id} | Visitor bearer; typed tool/arguments/event_id/locale; schema/permissions/consent; quota and fingerprint |
| POST /widget/v1/verify-email/{public_id} | Same visitor; bounded code delivery/verification, no returned code |
| GET /widget/manage/{public_id} | Standalone ownership-link UI; fragment capability, restrictive CSP |
| POST /widget/v1/manage/{public_id} | Signed email proof; details/live alternatives/confirmed reschedule/cancel |
| POST /widget/v1/recover/{public_id} | Visitor + fresh email proof; queues link only |
| /api/google/* | Tenant admin only: configure/connect/callback/revoke; encrypted tokens |
| /api/concierge/policy, requests, email-jobs | Private tenant admin policy/intake/diagnostics |

Tools: ConciergeAvailability, ConciergeBooking, ConciergeManage, ConciergeRequest. These extend the existing registry/executor rather than create another agent. Visitors cannot select tenant, calendar, sender, recipient for arbitrary mail, Google token, internal tool or another conversation. Unknown extra fields/tool names fail. Calendar writes need owner operations authorization, verified email/ownership and explicit consent.

Event IDs are scoped to session/conversation and reuse immutable payloads on retry. A changed fingerprint fails; uncertain external outcomes remain unresolved until reconciled. Receipts contain sanitized status/reference/time, locale/correlation and duplicate flag. Error codes include google_not_connected, live_operations_not_authorized, outside_booking_window, slot_unavailable, verification_required, ownership_required, stale_event, delivery_unknown and limit_reached; clients localize them without rendering private provider responses.

Deploy backend/API/widget assets first, then the independent website public HTTPS build. Cache/lifecycle events remain compatible with v1. Roll back website separately or disable paired public settings; unpublish the widget to block new sessions. A source rollback must not silently delete real events/mail or restore unrelated clinic policy. Feature pushes are authorized by the user only after completion; public deployment and real Google tests need separate explicit approval.
