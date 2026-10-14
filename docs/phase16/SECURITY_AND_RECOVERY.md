# Security and recovery

No destructive schema migration: existing schema5/store is reused. Tenant/RBAC tests cover queue assignment, lead reveal/CAS, quality reporting/review, usage and internal targets. Google owner JWT signature/issuer/audience/email/nonce/PKCE/cookie/replay checks remain; credentials load from fixed named secrets into backend memory. No raw Google callback code/token was inspected or placed in Git. Cross-origin iframe keeps visitor authority separate from staff identity.

New frozen source tests pass328 cases. Source boundary236 files/zero failures; offline redacted source scan2.61MB/no leaks; backend Docker build includes Gitleaks. Website public-config canaries pass from fresh baseline. No proprietary semantic runtime/import added; `semantic_os_for_ai` and unrelated cloud runtimes remain untouched.

Actual isolated encrypted SQLite backup/restore, WAL committed-data integrity, wrong-key/tampered-manifest rejection and no overwrite tests execute in `test_saas.py`. This does not certify deployed disaster recovery, key custody rotation, legal compliance or production RPO/RTO. Existing restore targets a new path and verifies integrity/FKs. Financial correction records are immutable and retained separately from erasable communication metadata.

Public synthetic host has only TCP80/443 and IAP-only SSH; no local Windows or Asterisk service is exposed. Backend non-root/read-only filesystem, protected new key, tenant data volume, fixed stop, public egress quota, owner-only admin and public staff-API404 boundary are configured/verified.


Evidence checkpoint: 11 October 2026, Europe/Sofia. Code is on separate `codex/phase16-saas-operations` branches. No Phase 16 main push/merge or production website deployment. Local feature scope was explicitly approved; the isolated synthetic HTTPS host and Google setup were subsequently authorized. Real Calendar/email actions and real payments remain separately gated.

Executed commands: `.venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests` (328 passed,101.860s; `artifacts/phase16/release-backend.txt`); frontend `npm.cmd test` (31 passed; `verified-frontend.txt`), `npm.cmd run lint -- --fix`, `npm.cmd run typecheck`, `npm.cmd run build`; Docker production-auth frontend build and backend image build with redacted Gitleaks; `python scripts/check_source.py` (236 files,0 failures); network-disabled redacted source scan (434 non-ignored files,2.61MB,no leaks). Logs are ignored under `artifacts/phase16`. These results do not certify legal compliance, live voice, provider billing or physical devices.

Owner/external gates: scoped public staging browser approval is pending after automatic review rejected inspection outside the prior local synthetic scope; actual iOS/Android and screen-reader access are unavailable; English live reschedule/mail receipt, actual reminder delivery, human-heard voice and real billing-provider certification remain unverified. No unexecuted check is PASS.


## Local browser integration checkpoint

Approved local Phase15 Synthetic Workspace, 320px Chromium viewport: Health Center failure exposed a missing default clock; fixed to reuse billing/runtime clock and covered by a new regression. Full backend328 tests pass in101.860s. Health loads in Bulgarian; Usage loads without alerts, switches to English, menu expands/closes and route focus moves to main. Document scrollWidth305 equals clientWidth305. Main content initially started817.4px below the top; measured mobile menu fix places it244.4px below the top, and route navigation focuses it. This is local synthetic geometry/keyboard evidence, not physical-device/screen-reader or final public browser acceptance. Captures: artifacts/phase16/browser/local-health-320.png and local-usage-320.png; earlier health capture is the before image. No real conversation or callback was inspected.
