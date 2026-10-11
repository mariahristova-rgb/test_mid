# Durable email and reminders

Gmail is a separate owner-authorized sending connection (gmail.send, no mailbox reading). Messages are plain-text MIME with deterministic Message-ID and encrypted server-side bodies. From uses the verified connected account; clients cannot choose arbitrary sender/attachments.

Google invitations provide booking/update/cancel confirmation. Separate management emails have a distinct purpose. Reminders are due at 08:00 Europe/Sofia on the meeting day when future; same-day later bookings use configured fallback minutes before the meeting if still feasible. No reminder is scheduled in the past. Pending jobs are canceled on reschedule/cancel. Before sending a booking-related job the worker checks current local/Google status and time; stale externally changed/canceled meetings are skipped. Delivery time itself cannot be controlled once Google accepts a message.

The existing maintenance loop runs bounded jobs outside the RTP/voice inference worker pool. Operations authorization and connections are checked. Jobs persist queued/sending/sent/blocked/delivery_unknown states. Explicit 429 rejection gets bounded exponential retries; denied/preflight failures may be retried by an admin after reconnect. Gmail provides no idempotency-key guarantee: timeout/uncertain sends or a crash in sending state require manual reconciliation, never blind replay. This favors preventing duplicate mail over pretending exactly-once delivery through an unknown network outcome.

Verification emails contain short-lived codes and are not sent after their proof expires or is already used. Product emails contain approved public links only; marketing consent is recorded separately and does not subscribe/send a campaign automatically. Business/feature messages go only to the configured business inbox.

Admin diagnostics: GET /api/concierge/email-jobs; retry permits only definitely blocked/rejected jobs, not uncertain sends. Real sending/inbox delivery and same-day behavior remain NOT RUN until owner Gmail OAuth and explicit live-test approval. Current local jobs cannot send because live operations are disabled.
