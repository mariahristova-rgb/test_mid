# Channel adapters

The domain `ChannelAdapter` exposes validation, normalization, configured recipient resolution, send, status parsing and error handling. Legacy mock methods remain for direct Web Chat/voice compatibility. `EmailProvider` and `SMSProvider` are provider-independent outbound ports. Business agent execution never imports a vendor SDK.

| Channel | Default implementation | Optional implementation | Verified status |
|---|---|---|---|
| Web Chat | Existing authenticated conversation APIs and mock response | Connection adapter for synthetic ingress/outbox | Offline + browser |
| Voice | Existing signed call gateway, bidirectional synthetic audio | Gated Twilio/Azure infrastructure from Phase 3 | Mock only; real speech/calls unverified |
| Email | Signed MIME/JSON connector + mock delivery | TLS SMTP outbound | Offline contracts; real mailbox/SMTP unverified |
| WhatsApp | Signed mock adapter | Official Cloud API payload/signature shapes and gated Graph send | Synthetic signatures/contracts only |
| SMS | Signed mock adapter | Twilio form webhooks, official SDK signature validator and gated REST send | Synthetic signatures/contracts only |

Canonical Message fields include original external message ID, sender/recipient IDs, direction, content/type, structured attachments, detected/active locale, timestamp, delivery status, correlation and metadata. Legacy `external_id`, `sender`, `recipient`, `locale`, `type` aliases are retained. Provider events cannot supply a principal, tool grant or arbitrary conversation ID.

## Local connector contract

Configure an encrypted connection with `POST /api/messaging/connections` (admin). `mock` requires a webhook secret of at least 32 characters and a configured sender address/number. `web_chat` accepts a logical sender ID. Configure the assistant to enable the desired channel first.

Send UTF-8 JSON to `POST /webhooks/messaging/{tenant}/{connection}` with `X-Signature` equal to the hex SHA-256 HMAC of the exact bytes:

```json
{
  "external_message_id": "synthetic-provider-id",
  "sender_id": "+359888000002",
  "recipient_id": "+359888000001",
  "content": "Здравейте, искам да запиша час за утре в 15:00.",
  "timestamp": "2030-01-10T09:00:00+00:00",
  "metadata": {}
}
```

Timestamp must be aware, within the configured maximum age (default seven days), and at most five minutes in the future. An email connector must additionally attest `metadata.sender_verified: true` as a Boolean after checking sender identity. MIME ingestion accepts `mime_base64` and top-level `sender_verified: true`. This attestation belongs to a trusted connector; a customer-supplied email header is not a verification grant.

Synthetic callback JSON has `kind: "status"`, `event_id`, `provider_message_id`, `status` (sent/delivered/read/failed), and optional `message_id`. Real Meta/Twilio shapes are normalized by their own adapters. Run due jobs separately; HTTP ingress does not execute agents or send network messages.

Capabilities and connection state are tenant scoped. Configuration responses contain credential names, never credential values. Live delivery requires both `ASSISTANT_ENABLE_LIVE_MESSAGING=true` and `enable_live=true` on the connection. Mock adapters never use that flag. Disable/re-enable via `/api/messaging/connections/{id}/state`. Disabled users and revoked roles are checked again when work executes.

Run `python scripts/demo_multichannel.py --output docs/architecture/MULTICHANNEL_DEMO.json` for all four signed offline scenarios. See individual integration documents for provider configuration and remaining live gates.
