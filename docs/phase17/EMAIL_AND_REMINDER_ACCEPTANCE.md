# Email and reminder acceptance

Existing concierge scheduler uses 08:00 Europe/Sofia on the meeting date; if already passed, start minus configured fallback minutes, only when now < due < start. Keys include booking ID/revision; reschedule/cancel cancels stale jobs. Live-operation gating remains off outside approved tests.

Offline corpus verifies no duplicate reminder dispatch/late send and `delivery_unknown` after uncertain Gmail send without automatic replay. These are simulated clock/transport tests. BG owner-confirmed historical mail receipt is recorded in Phase15; EN human receipt and a real reminder acceptance remain pending.

Gmail API acceptance is not inbox delivery. Operator recovery must reconcile uncertain sends, never convert unknown into successful delivery or replay merely to clear an alert. Live recipient/action approval is required; no email was sent by Phase17.

Acceptance may combine controlled scheduler-clock tests and one approved live reminder email, with explicit simulation labels. Production same-day delivery and queue-worker crash/restart proof remain open.
