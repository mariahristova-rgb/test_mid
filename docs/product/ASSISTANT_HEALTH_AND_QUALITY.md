# Health and human-reviewed quality

11 October 2026. Local feature branch `codex/phase15-product-experience`; no Phase 15 push/merge/public deployment. Existing URLs and the two-agent runtime are retained.


Current source has ux.readiness, provider descriptors, Google status, jobs and privacy-redacted conversation diagnostics. Phase15 fixes diagnostic availability coverage to recognize ConciergeAvailability and derives booking state from persisted appointments when the legacy mock booking_state is absent. This prevents a real concierge cancellation appearing unrecorded in metadata diagnostics.

Planned shared health projection reuses these records; no new analytics store or autonomous training loop. Per-channel configured/simulated/tested/live-receipt dates must remain distinct. Calendar create/reschedule/cancel have named receipts; actual reminder delivery and human-audible voice do not.

Quality Coach is NOT_IMPLEMENTED (P1 gate). Proposed deterministic categories: provider failure, invalid tool input, ambiguous consent, locale mismatch, excessive measured latency, repeated handoffs and approved-knowledge fallback. Count/rank metadata within bounded time windows, link only to tenant-scoped redacted evidence, generate a proposed synthetic regression case for human approval. Never copy raw live transcripts into tests, change instructions/tools, retrain or auto-publish.

Credential expiry, uncertain Gmail sends and unknown calendar writes require explicit operator reconciliation; never blind retry. Existing Gmail unknown-send policy and deterministic event IDs are retained. Queue notes are audit-read, expire with tenant conversation retention and are redacted by bounded maintenance.


## Opt-in Google owner identity

New google_owner_login.py plugs into existing IdentityService. RS256 Google JWKS, exact web-client audience/issuer, verified pinned owner email, nonce, PKCE, HttpOnly secure browser binding, consumed states,60-second one-use fragment tickets, existing membership/revocation and encrypted transient material are tested. It creates membership only in the server-configured staging tenant and never upgrades an existing role. Google access/refresh tokens from the sign-in response are discarded. Calendar/Gmail connections remain separate consent flows. Frontend stores the signed ID token in memory; no credential goes into a public widget or localStorage.

Real hosted owner sign-in is IMPLEMENTED_UNVERIFIED until DNS/TLS, exact client callback registration, scoped metadata identity approval and owner interaction succeed. No Auth0 domain/audience is synthesized from G_CLIENT values. Source: google_owner_login.py, google_secret_manager.py, api.py, frontend/services/api.ts; unit tests include JWT/nonce/replay/expiry/role/tenant checks and actual HTTPS route cookie/ticket contracts.
