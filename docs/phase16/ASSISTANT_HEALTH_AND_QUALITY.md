# Assistant health and quality

Paths: `customer_workspace.py`, `ux.py`, `api.py` maintenance, `privacy.py`, `CustomerWorkspaceView.vue`, `InboxQueue.vue`. Health presents FAQ counts, language coverage, tool count, agent enablement, draft/readiness, publication identifiers, stored connectivity and failed jobs. Configured/connected is not production certification; voice_live_verified staysfalse.

Coach is a structured rule-based projection, not transcript analysis or autonomous LLM tuning. It groups failed test/job/tool records and recorded unclear voice metadata when present. Operators can explicitly report eight categorical issues: STT uncertainty, ambiguous consent, tool denial, outage, knowledge gap, invalid answer, duplicate action, abandonment. Reports are marked OPERATOR_REPORTED, deduplicated, role/tenant bound and retained at most7days. No raw text/contact is copied.

Accept/dismiss records provenance and reviewer; it cannot change prompts, permissions, live tools or publication. Suggested existing BG/EN scenarios require human adaptation/review for the actual failure. Expired sources are excluded; maintenance redacts expired reports/reviews. No numeric quality score or inferred abandonment rate is invented. Tests cover report/review immutability, isolation, replay and expiration.


Evidence checkpoint: 11 October 2026, Europe/Sofia. Code is on separate `codex/phase16-saas-operations` branches. No Phase 16 main push/merge or production website deployment. Local feature scope was explicitly approved; the isolated synthetic HTTPS host and Google setup were subsequently authorized. Real Calendar/email actions and real payments remain separately gated.

Executed commands: `.venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests` (328 passed,101.860s; `artifacts/phase16/release-backend.txt`); frontend `npm.cmd test` (31 passed; `verified-frontend.txt`), `npm.cmd run lint -- --fix`, `npm.cmd run typecheck`, `npm.cmd run build`; Docker production-auth frontend build and backend image build with redacted Gitleaks; `python scripts/check_source.py` (236 files,0 failures); network-disabled redacted source scan (434 non-ignored files,2.61MB,no leaks). Logs are ignored under `artifacts/phase16`. These results do not certify legal compliance, live voice, provider billing or physical devices.

Owner/external gates: scoped public staging browser approval is pending after automatic review rejected inspection outside the prior local synthetic scope; actual iOS/Android and screen-reader access are unavailable; English live reschedule/mail receipt, actual reminder delivery, human-heard voice and real billing-provider certification remain unverified. No unexecuted check is PASS.
