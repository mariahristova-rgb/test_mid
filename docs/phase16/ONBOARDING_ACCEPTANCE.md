# Onboarding acceptance

Paths: `customer_workspace.py:progress`, existing `ux.py`, `widget.py`, `SetupView.vue`, `WidgetView.vue`. Progress projects persisted verification/draft/tests/publication/domain/widget state. Readiness uses configuration/agent/business hashes, both languages, seven-day maximum receipt age and existing activation guards. Widget publication and rollback now require fresh passing receipts.

Drafts already resume from persistent records. Widget editor adds leave/reload guards and explicit discard; publishing rejects unsaved edits. Installation snippet copy and real nonce-domain verification are reused. The synthetic host verified `https://assistant-demo.ontelyx.tech` through actual HTTPS before publishing its FAQ-only widget.

Tests: `test_customer_workspace.py` progress/stale evidence/role checks and existing `test_ux.py`, `test_widget.py`, `test_public_staging_bootstrap.py` are in the327 passing suite. Actual complete customer usability, cohort tracking, slow network and physical device onboarding remain open.


Evidence checkpoint: 11 October 2026, Europe/Sofia. Code is on separate `codex/phase16-saas-operations` branches. No Phase 16 main push/merge or production website deployment. Local feature scope was explicitly approved; the isolated synthetic HTTPS host and Google setup were subsequently authorized. Real Calendar/email actions and real payments remain separately gated.

Executed commands: `.venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests` (328 passed,101.860s; `artifacts/phase16/release-backend.txt`); frontend `npm.cmd test` (31 passed; `verified-frontend.txt`), `npm.cmd run lint -- --fix`, `npm.cmd run typecheck`, `npm.cmd run build`; Docker production-auth frontend build and backend image build with redacted Gitleaks; `python scripts/check_source.py` (236 files,0 failures); network-disabled redacted source scan (434 non-ignored files,2.61MB,no leaks). Logs are ignored under `artifacts/phase16`. These results do not certify legal compliance, live voice, provider billing or physical devices.

Owner/external gates: scoped public staging browser approval is pending after automatic review rejected inspection outside the prior local synthetic scope; actual iOS/Android and screen-reader access are unavailable; English live reschedule/mail receipt, actual reminder delivery, human-heard voice and real billing-provider certification remain unverified. No unexecuted check is PASS.
