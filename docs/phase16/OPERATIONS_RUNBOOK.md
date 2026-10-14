# Operations runbook

Use existing `/operations` and new Health/Quality/Usage views under their normal roles. Review failed/dead-letter/uncertain jobs by correlation and source IDs; classify first. Never blindly replay unknown Google event/email writes. Check provider receipts and reconcile the original idempotency key before retry. Failed provider status is not a successful customer confirmation.

Internal latency/error/availability/window targets are tenant configurable; current error-budget evaluation is NOT_EVALUATED because the required observation window and p95/uptime series are absent. These are not a customer SLA. Temporary staging intentionally stops on its approved deadline. Queue backlog is bounded and labeled when truncated. Quota alerts are available; actual cost-anomaly detection is not.

Staging files: `deploy/phase15-staging/{compose.yml,Caddyfile,nginx.conf,startup.sh,install-package.sh,bootstrap.py}`; scripts `phase15_provision_staging.py`, `package_phase16_staging.py`, `phase16_staging_acceptance.py`. Do not rerun provisioning to create another host; it refuses replacement. Preserve the isolated encryption key/data. Restore only to a new offline database with provider jobs disabled. Do not copy the local all-tenant database, Google refresh tokens or model volumes.

Auth validation succeeded with owner-pinned Google OIDC. `G_CLIENT_ID2` had contained a callback URL; corrected to an alias of the actual existing client ID matching the owner-selected unchanged `G_CLIENT_SECRET`. Added only the staging owner-login callback to the existing web client; local Calendar callback preserved. New VM SA reads only those two names and has no project-wide roles. This is not a separate OAuth client, nor a public customer-signup identity rollout.


Evidence checkpoint: 11 October 2026, Europe/Sofia. Code is on separate `codex/phase16-saas-operations` branches. No Phase 16 main push/merge or production website deployment. Local feature scope was explicitly approved; the isolated synthetic HTTPS host and Google setup were subsequently authorized. Real Calendar/email actions and real payments remain separately gated.

Executed commands: `.venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests` (328 passed,101.860s; `artifacts/phase16/release-backend.txt`); frontend `npm.cmd test` (31 passed; `verified-frontend.txt`), `npm.cmd run lint -- --fix`, `npm.cmd run typecheck`, `npm.cmd run build`; Docker production-auth frontend build and backend image build with redacted Gitleaks; `python scripts/check_source.py` (236 files,0 failures); network-disabled redacted source scan (434 non-ignored files,2.61MB,no leaks). Logs are ignored under `artifacts/phase16`. These results do not certify legal compliance, live voice, provider billing or physical devices.

Owner/external gates: scoped public staging browser approval is pending after automatic review rejected inspection outside the prior local synthetic scope; actual iOS/Android and screen-reader access are unavailable; English live reschedule/mail receipt, actual reminder delivery, human-heard voice and real billing-provider certification remain unverified. No unexecuted check is PASS.


Default runtime clock integration fix: CustomerWorkspace falls back to the existing BillingService clock. A local real-browser Health Center check found the issue; regression and full328-case suite pass. Local demo services were updated only after a0-active-call check; Qwen/STT/TTS/Asterisk and their data were preserved.
