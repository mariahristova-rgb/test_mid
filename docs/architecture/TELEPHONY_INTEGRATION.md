# Telephony integration

Default: **MOCK**, no real calls. Infrastructure adapters for Twilio and Azure are installed but **LIVE_UNVERIFIED**. No test account, real number, credentialed speech request or real Bulgarian sample was exercised.

## Mock incoming and media

1. Set an owner-managed `ASSISTANT_ENCRYPTION_KEY` and enable only the local demo described in README.
2. Configure an assistant's typed `voice_settings` and keep providers `mock`.
3. POST `/api/telephony/connections` as its tenant administrator with assistant ID, synthetic E.164 `phone_number` and a random webhook secret (at least 32 characters). The response excludes credentials; storage encrypts the secret.
4. POST raw JSON `{call_id, from, to, status, event_id}` to `/webhooks/telephony/{tenant}/{connection}` with `X-Signature = hex HMAC-SHA256(raw body, secret)`. To-number and enabled tenant service membership must match. Duplicate provider call IDs reuse the session. Terminal callbacks cannot reopen it.
5. POST `/api/calls/{id}/stream-ticket` with `confirmed:true`, then connect `/voice/media` and send `{event:'start',ticket}`. The browser Calls view performs this for synthetic sessions.
6. Send `media` events with bounded AudioFrame fields, or mock-only final/partial `recognition` events. Fixture bytes are UTF-8, not playable audio. Stop/close ends the session; call history and usage remain persisted.

Authenticated `/api/calls/{id}/events` retains manual synthetic lifecycle controls and permission-checked structured tool requests. Real provider transcripts cannot be supplied through that synthetic endpoint. Call event/participant/usage/execution history is at GET `/api/calls/{id}/events`; plaintext transcript retrieval is administrator-only and retention-scoped.

## Gated Twilio + Azure setup

Only an explicitly authorized test account/number should be configured for live evaluation. Source implementation is not authorization to make a real call. The application provides no outbound-call creation endpoint; transfer controls only an already existing incoming call and a configured human destination.

Required settings:

- Backend `ASSISTANT_ENABLE_LIVE_VOICE=true`, only after owner authorization. Unset/false blocks live operation.
- Managed encryption key and verified tenant service membership with required tool grants.
- Assistant voice settings: telephony `twilio`, recognition/synthesis `azure`, explicitly selected initial locale, matching locale voices, greetings/notices, timeouts and configured E.164 escalation destination.
- Twilio test Account SID, Auth Token and incoming E.164 number; HTTPS public origin serving the webhook and WSS endpoint.
- Azure Speech key, resource name and matching region. Credentials are supplied to the administrator API and stored encrypted, not in browser build variables or logs.
- Per-connection `enable_live:true` in addition to the global gate. Credential presence alone never activates live operation.

POST `/api/telephony/connections` with non-secret fields `provider`, `assistant_id`, `phone_number`, `public_origin`, `account_sid`, `speech_resource`, `speech_region`, `enable_live`, plus secret fields `auth_token`/`speech_key`. Use placeholders in examples and a secret manager for actual values. Both configured TTS voices are validated before activation. Recording remains off until caller opt-in; policy configuration is permission, not automatic recording.

Set the number's incoming/status POST webhook to `/webhooks/telephony/{tenant}/{connection}` under the exact configured public origin, with no query string. The adapter verifies Twilio's canonical-URL/form HMAC signature, account and number binding. It refuses duplicate form keys rather than interpreting them inconsistently. It returns `<Connect><Stream>` TwiML with a one-use custom parameter. See [Twilio Media Streams](https://www.twilio.com/docs/voice/media-streams) and [Stream parameters](https://www.twilio.com/docs/voice/twiml/stream).

The WebSocket adapter accepts connected/start/media/mark/stop messages, verifies the upgrade signature against the configured HTTPS origin, validates call/account/format and emits headerless base64 mu-law/8000 media. A `clear` message interrupts buffered output, following [Twilio's media-message contract](https://www.twilio.com/docs/voice/media-streams/websocket-messages). Reverse-proxy Host/forwarded headers never substitute for the configured signature URL; canonical URL/signature interoperability still needs real-account validation.

Incoming 8kHz mu-law is decoded to PCM and converted to 16kHz mono WAV for Azure's short-audio endpoint. This REST adapter returns final utterance recognition, not streaming partial hypotheses or automatic acoustic language identification. TTS uses escaped SSML and raw 8kHz mu-law output. See [Azure short-audio STT](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-speech-to-text-short) and [Azure TTS REST formats](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech). HTTP requests are bounded and use fixed vendor hosts; provider exceptions are reduced to safe codes. No additional vendor SDK dependency was introduced.

## Remaining live requirements

Validate WSS/TLS/firewall/reverse-proxy handling, signature canonicalization, real carrier/SIP routing, calls/status/transfer, audio quality, actual STT/TTS locales, utterance latency and barge-in, noise/echo, caller notice/consent, interrupted actions and billing reconciliation. Replace sample-duplication conversion/simple VAD if real audio tests require it. Direct SIP URIs, complete SIP signaling, carrier recording and acoustic language ID are not implemented. HTTP speech is utterance-based; a tested streaming Speech SDK provider can implement the existing ports later.

Use the authorized test number/account only. Never interpret fake HTTP contract tests or provider language documentation as live telephone verification.
