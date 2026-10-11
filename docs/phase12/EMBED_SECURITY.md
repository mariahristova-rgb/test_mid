# Embed security and limitations

The public `wdg_…` identifier is not an API key or identity. Staff endpoints require existing authenticated tenant membership/RBAC; visitor credentials fail those checks. Public requests cannot choose a tenant, assistant, conversation or tool.

## Capability flow

Exact verified website Origin permits a 60-second, single-use admission ticket. The host passes only this ticket to the separate-origin iframe. Redemption binds integration, tenant, parent origin, published version and epoch, creates a private conversation, and returns a random 10-minute chat capability. Only its SHA-256 hash is persisted. The iframe keeps the capability in memory; no URL, cookie or localStorage stores it. Closing/reopening the same iframe retains the in-memory session; reloading loses it. No durable anonymous account or cross-device reconnect is provided.

Each message checks lifecycle, epoch, TTL, snapshot policy, quotas and conversation binding again within the action transaction. Retries reuse an event ID; changed payloads with the same ID fail. Failed runtime attempts still consume quota; identical retries do not. Configuration changes, domain challenges, publish, rollback, unpublish and revoke invalidate old sessions. A revoked ID cannot be republished.

Configured daily admission limits are 1–500/integration; messages 10–3000/integration. Tenant caps are 1000 admissions and 5000 unique message attempts/day; each session allows 60 attempts. Counters persist in SQLite and use UTC calendar days. These bound anonymous business access, not volumetric network denial of service. Distributed rate limiting, edge/IP abuse controls, challenge mechanisms and metadata compaction are staging prerequisites.

## Browser policies

Admission CORS reflects only the verified exact origin, permits POST/Content-Type and never credentials. Omitted/null/unlisted origins fail. Widget POSTs require the dedicated widget Origin. Non-browser clients can forge Origin: domain ownership proves authorization to embed, not visitor identity, and is not bot prevention. Quotas and restricted capabilities remain necessary.

The loader uses a closed Shadow DOM and lazy iframe. Both sides validate message window source, exact origin, namespace, public ID, random nonce and permitted schema keys; postMessage targets an exact origin. The iframe uses `allow-scripts allow-same-origin` on a dedicated origin, with microphone/camera/geolocation denied. Its CSP restricts scripts/styles/connections to self and frame ancestors to the verified parent; no inline scripts, eval or tenant HTML. Staff pages retain frame denial. Text uses textContent. Colors are strict hex; logos require HTTPS and can disclose visitor IP to a third party. Prefer a controlled static image host and explain it in the privacy notice.

Official policy references: [MDN postMessage](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage), [MDN iframe sandbox](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe), [MDN frame-ancestors](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors). Nested CMS frames must satisfy the ancestor policy; compatibility is not certified by reading documentation.

## Domain proof and tools

Nonce fetching uses a fixed path, a three-second timeout, pinned DNS address, public-address checks, TLS hostname verification, no proxy/redirect, text/plain and at most 512 bytes. HTTP loopback is allowed only for explicitly configured development sites. The local Docker override maps the exact 3021 example origin to its isolated sample container; production ignores all demo targets.

Visitor snapshots restrict tools to CheckAvailability, CreateAppointment and EscalateToHuman when enabled. Booking requires details and explicit consent through the existing executor/approval workflow. Arbitrary client tool arguments, cancellation/rescheduling and outbound sends are unavailable. Current widget promotion permits mock LLM/calendar only; it does not verify a real inference provider. Prompt text never grants additional server authority.

## Privacy and retention

Language preference storage requires the checkbox; chat itself needs no persistent browser storage. Clear requires explicit confirmation and redacts message text/attachments and provider-result copies, cancels pending approvals, closes the conversation and disables the session. The same hashed credential can request deletion after expiry or revocation. Scheduled bounded retention cleanup applies the configured 1–30 days, no longer than tenant policy.

Appointments, contact/business fields in booking state and tool/agent/audit records are retained separately. Clear is **not complete erasure of every business record**; use authenticated business privacy procedures for those records and backups. Metadata/counters are retained, so long-term compaction and a verified deletion/backup policy remain required before public staging. No sensitive customer data was used for this demo.
