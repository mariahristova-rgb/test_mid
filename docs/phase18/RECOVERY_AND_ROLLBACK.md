# Local recovery and rollback checklist

13October2026. Existing mechanisms reused; no new public control endpoint.

1. Network failure in iframe: preserve pending event/payload; reconnect alone does not resend; explicit retry uses the original ID. Expiry clears execution authority and requests a fresh frame/session, never auto-confirms.
2. Calendar unknown: retain original intent/event ID; inspect authorized provider state before any operator decision. A successful immediate readback completes a committed create once. Unobservable/mismatched responses remain unknown; no blind retry or invented success. Manual downstream reconciliation is still required for unresolved cases.
3. Gmail unknown: persisted delivery_unknown is not inbox receipt. Never reset to pending without separately authorized reconciliation. Disconnect/live flag blocks new delivery; no token migration.
4. Disable: existing widget unpublish/revoke invalidates session epoch; old session remains rejected even after rollback. Fresh admission needed. Tests execute this lifecycle and allow clear after revocation.
5. Restore: existing encrypted backup restores to a new isolated path, validates integrity/FKs and refuses overwrite. Never restore customer data into public staging or enable live workers on an unreviewed restore.
6. Code rollback: revert only Phase18 checkpoint on feature branch. API/schema remain unchanged; no migration/downmigration or production deployment occurred. Rolling back removes the new guards, so preserve regression evidence for review.

Validated here: Node VM recovery, isolated publication rollback, database reopen/encrypted restore, synthetic uncertainty/replay checks. Not validated: deployed worker crash/DR, device browser reconnect or live Google recovery. Host stop14October20:57Europe/Sofia and standing disk/IP costs are unchanged.
