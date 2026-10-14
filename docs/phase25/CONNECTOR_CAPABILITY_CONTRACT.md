# Connector capability contract v1

Implemented local paths: catalog/connections/create/test/disconnect, per-connection oauth/start, oauth/complete, resources and preview; quotes list/create. All require authenticated configure permission, explicit local fixture enablement and a non-strict demo environment. Provider availability remains COMING_SOON for customer self-service. `simulation=true` is never an activation grant.

Google/Outlook fixtures support availability/create/reschedule/cancel codecs; Calendly supports availability/scheduled-events reads; HubSpot supports contact read/write. Unsupported actions fail before transport. No uniform provider promise. Connection actions/resources are allowlisted. Preview writes require consent; their ownership is explicitly synthetic and does not constitute a real booking-ownership proof.

Create deduplicates canonical configuration within tenant. Preview binds connection, revision, key and payload fingerprint; cached completed receipts return once, pending/unknown cannot replay, changed payload conflicts. OAuth binds tenant/user/subject/connection/revision, state, browser binding and expiry. Responses do not expose token bundles. Default/live HTTP transports are refused.

No DDL or existing endpoint deletion. SubscriptionPlan gains optional connector_limit and connector_providers fields; legacy plans retain behavior. Existing booking orchestration remains authoritative and unchanged. New fixture previews do not create application appointments or send notifications; they test provider codecs only.
