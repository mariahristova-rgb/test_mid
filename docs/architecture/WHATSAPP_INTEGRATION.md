# WhatsApp Business integration

Default mock delivery sends nothing externally. The optional Meta adapter supports official Cloud API-shaped text/button/interactive/media events, account/phone-number binding, SHA-256 app-secret signatures, GET challenge verification, outbound text/templates and signed sent/delivered/read/failed callbacks. Tested with signed synthetic events; no Business account was registered and no real WhatsApp message was sent.

Configure provider `meta`, sender_id (E.164), waba_id, phone_number_id, configurable Graph api_version, public_origin, encrypted app_secret, verify_token and access_token. The API version must be selected from the deployed account's supported versions; no current version is assumed. Use least-privilege official Business permissions. Live sends require both server and connection enable flags.

Use `https://<origin>/webhooks/messaging/<tenant>/<connection>` for verification and message/template callbacks. Signatures use the exact raw body; WABA and phone_number_id must match the connection. Query token verification is constant-time. Disable proxy/server query logging; the supplied container uses `--no-access-log`.

Inside the customer service window, free-form replies use the originating conversation. The last customer timestamp must be within 24 hours and not in the future. Outside the window, a tenant/connection/key/locale-specific approved template and recorded WhatsApp consent are mandatory. Automated notifications require consent even inside the window. Missing permissions/templates/consent enter the review queue instead of sending.

Register a template mapping using `/api/messaging/templates` with provider_name, internal template_key and bg-BG/en-US. Real Meta mappings start pending; an admin cannot assert production approval. A signed template-status callback verifies approval/rejection. Mock mappings can be fixture-approved. Template selection uses `bg` and `en_US`; variables are explicit strings, not executable instructions. Phone account rate limits are bounded locally; provider 429 uses safe backoff. Provider acceptance remains LIVE_UNVERIFIED.

Media stores protected provider identifiers and metadata; no arbitrary URL fetch or media auto-execution occurs. Supported uploaded types remain quarantined. Unsupported media is rejected into review. Account onboarding, business verification, approved template creation/content matching, credential rotation, current provider policy review and live bilingual end-to-end tests remain required.

Primary references: [Meta webhook signature/challenge documentation](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/webhooks/start/), [official Business messaging documentation](https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages). The current Meta documentation endpoint rate-limited this audit; synthetic contract compatibility is not a claim of live account compatibility.
