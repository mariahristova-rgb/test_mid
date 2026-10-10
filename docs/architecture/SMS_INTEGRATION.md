# SMS integration

The SMSProvider port supports a no-send mock and optional gated Twilio REST delivery. Inbound/outbound messages, E.164 normalization, Unicode preservation, callbacks, opt-out, retries, segment accounting and tenant credentials are implemented. Real SMS delivery, actual billing and sender registration are unverified.

Install `requirements-messaging.txt` for the official Twilio SDK RequestValidator. Configure provider `twilio`, sender_id, account_sid, public_origin and encrypted auth_token. Form webhook validation uses the configured HTTPS origin plus the exact path, never an attacker-supplied Host header. All form fields participate in the SDK signature, duplicate keys are rejected, and AccountSid/To must match. StatusCallback is `/webhooks/messaging/{tenant}/{connection}/status/{local-message-id}` and must validate the same signature/account.

GSM-7 counts extension characters as two units: 160 units for a single segment, 153 per multipart segment. Unicode uses UTF-16 units: 70/67 units; Cyrillic is retained and emoji surrogate pairs count as two. Usage exposes encoding, units and segments; price is unknown. Splitting is the provider's job; the application preserves complete content.

STOP and localized stop commands mark an endpoint contact opted out. The opt-out acknowledgment is allowed once per unique inbound event; later automated or human sends are blocked. Automated reminders and scheduled SMS require explicit recorded sms_consent. `/api/contacts/{id}/consent` records operator identity, timestamp and evidence; it does not clear opt-out. No marketing engine or automatic re-enrollment is implemented.

Delivery `simulated` is a mock result, `sent` is provider acceptance, `delivered` requires a signed callback. Callback downgrade and cross-connection attempts are rejected/ignored. Explicit 429 rejection can retry with backoff; timeouts/unknown acceptance do not. Provider-specific sender restrictions, jurisdiction opt-in policy, live carrier tests and cost reconciliation remain deployment work.

Primary references: [Twilio messaging webhooks](https://www.twilio.com/docs/messaging/guides/webhook-request), [Message resource and encoding](https://www.twilio.com/docs/messaging/api/message-resource).
