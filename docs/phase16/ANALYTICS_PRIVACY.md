# Analytics privacy

Paths: `journey.py`, `widget.py`, `privacy.py`, `customer_workspace.py`, `widget/{frame.html,frame.js,catalog.js}`, `WidgetView.vue`. Analytics is off by default and requires owner enablement in the published widget version plus an unchecked explicit visitor opt-in. First-party events carry stage, locale, channel, assistant reference and time; no message/contact/browser history is copied.

Measured stages: opted-in widget present, successful conversation turn, availability tool completion, proposal, calendar tool completion, inquiry record and human request. Count once per conversation/consent interval. Mock and connected-provider receipts are distinct. All impressions/opened sessions, sales qualification, reminder receipt, attendance, revenue and cohort drop-off remain unmeasured.

Retention is at most7days and bounded by widget retention. Withdrawal survives expired sessions, redacts prior events and prevents stale observers restoring consent. Chat clear, expiration and explicit erasure exclude events; no data restoration on re-consent. Operational record counts include cancelled/synthetic data and are not conversion. Structured quality signals have separate categorical purpose/retention. Tests verify opt-in, replay, withdrawal race, expiry and content exclusion.


Evidence checkpoint: 11 October 2026, Europe/Sofia. Code is on separate `codex/phase16-saas-operations` branches. No Phase 16 main push/merge or production website deployment. Local feature scope was explicitly approved; the isolated synthetic HTTPS host and Google setup were subsequently authorized. Real Calendar/email actions and real payments remain separately gated.

Executed commands: `.venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests` (328 passed,101.860s; `artifacts/phase16/release-backend.txt`); frontend `npm.cmd test` (31 passed; `verified-frontend.txt`), `npm.cmd run lint -- --fix`, `npm.cmd run typecheck`, `npm.cmd run build`; Docker production-auth frontend build and backend image build with redacted Gitleaks; `python scripts/check_source.py` (236 files,0 failures); network-disabled redacted source scan (434 non-ignored files,2.61MB,no leaks). Logs are ignored under `artifacts/phase16`. These results do not certify legal compliance, live voice, provider billing or physical devices.

Owner/external gates: scoped public staging browser approval is pending after automatic review rejected inspection outside the prior local synthetic scope; actual iOS/Android and screen-reader access are unavailable; English live reschedule/mail receipt, actual reminder delivery, human-heard voice and real billing-provider certification remain unverified. No unexecuted check is PASS.
