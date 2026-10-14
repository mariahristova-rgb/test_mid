# Google customer booking acceptance
Local implementation: availability and confirmed creation via the existing two agents, tool permissions, approval transaction, appointments, audit and durable jobs. Visitor confirmation queues pending_external; a provider receipt is required before confirmed status. Web Chat polls only its bound booking receipt. Repeated confirmation cannot create a second job/event. Stable event IDs support GET-only reconciliation after an unknown write.

Business timezone, hours, duration, buffer, notice, holidays and unavailable periods reuse existing policy validation. Explicit customer-calendar activation captures a policy snapshot, verifies owned-resource access and blocks unresolved approvals/calls/jobs. Mock draft activation cannot silently change the active customer policy. Cancellation/rescheduling on customer_google are denied until their provider workflow is reviewed.

Evidence: BG and EN synthetic two-agent creation, duplicate confirmation, disconnect-before-write, closed day, DST ambiguity, policy snapshot, disabled configuration and unknown-write reconciliation pass. No live Google requests, events, email/invitations or customer accounts were used. sendUpdates=none; no attendee invitation is claimed.

Live gate remains BLOCKED: reviewed customer application, actual account consent, isolated calendar, redacted create/reconcile/disconnect receipts and explicit write authorization. OFFLINE_PASS is not LIVE_VERIFIED.
