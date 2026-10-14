# Deployment compatibility and readiness

No deployment in Phase20. Existing files: semantic_os/deploy/phase15-staging/{compose.yml,bootstrap.py,Caddyfile,nginx.conf}; existing package/hashes verified locally. Current remote DNS/TLS/host/image state NOT_TESTED; Phase16live receipts remain dated historical evidence.

| Component | Contract/config | Compatibility evidence / remaining gate |
|---|---|---|
| Website Vue/Vite | Validated public origin/widget ID; no privileged secrets |78fresh tests/config/typecheck/buildPASS; approved dependency patch only |
| Loader/iframe | testmid-widget-v1 nonce/origin/scoped capability | Phase19VM/source testsPASS; public browser gate absent |
| Public API/typed actions | Existing /widget routes, BG/EN/locale/timezone | Existing synthetic ownership/replay tests; no wire/schema changes |
| Staff API | Owner Google login, tenant RBAC; public proxy denies staff routes | Fresh owner regression tests; hosted login/config not rechecked |
| Assistant/config | Existing revision snapshots/fresh test receipts | Same corpus1.2.0; no real-model or live-tool certification |
| Persistence/jobs | SQLite schema5, one process, persistent volume | Phase19migration/restore/no-replay tests; no deployedDR |
| Runtime artifacts | Reviewed backend/frontend tags; pinned proxy digests | Local config hashesPASS; source-to-OCI/deployed parity NOT_TESTED |

Staging is recorded as isolated FAQ-only tenant, mock LLM/billing, live voice/messaging disabled. Google owner OIDC references fixed secrets server-side; original local Calendar/Gmail tokens/database/key must not be migrated. Public TLS terminates at Caddy; TCP80/443 only, IAP SSH policy recorded earlier. Correct DNS/TLS/CSP/CORS and staff boundaries need fresh approved remote checks; never infer HTTPS from manifest text alone.

Model/voice/SIP remain separate resource domains; e2-micro cannot be presumed to host Qwen. One backend process owns SQLite and local scheduler locks. No replicas/HA; external distributed adapter/queue/locking/migration/restore design requires separate approval before expanded topology.

Rollback/disable reuse widget unpublish/revoke/epoch and compatible image/source receipts; do not revive old visitor authority or blindly reset unknown jobs. Code rollback restores this phase's website lockfile only; broader source checkpoints remain preserved. Hosting deadline14October20:57Europe/Sofia not extended; current costs unavailable.
