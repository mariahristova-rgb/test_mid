# Mobile and website acceptance

Website remains independent Vue3/Vite; Phase16 website runtime/layout/SEO is unchanged. Paths: website `src/{config.ts,assistant-contract.ts,assistant-labels.ts,components/AiAssistantEntry.vue,views/AiAssistantView.vue}`. Existing hosted config rejects localhost/private origins. The local website build is a preview, not a publishable localhost artifact.

Widget uses existing lazy loader and cross-origin iframe. Public Shadow DOM container is now open for diagnostics/standard browser tests; CSS isolation and iframe credential boundary remain. Tokens remain in iframe memory, not loader attributes or parent messages. Reduced-motion/safe-area/visual-viewport foundations are retained.

Verified before the final update: real HTTPS synthetic page, rendered widget greeting and keyboard launcher opening; owner Google sign-in landed on synthetic Overview. Final updated BG/EN approved FAQ, replay, clear and401/404 boundaries pass HTTPS protocol tests. These are not final browser usability proof. Public staging browser inspection was rejected by auto-review for scope beyond the earlier local synthetic permission; explicit scoped approval is pending. Physical iOS/Android, screen reader,200%zoom and slow network remain unverified. No unverified browser voice activated.

The production Ontelyx widget ID/origin was not switched to this FAQ-only staging tenant; real demo lifecycle and notification certification remain separately gated.


Evidence checkpoint: 11 October 2026, Europe/Sofia. Code is on separate `codex/phase16-saas-operations` branches. No Phase 16 main push/merge or production website deployment. Local feature scope was explicitly approved; the isolated synthetic HTTPS host and Google setup were subsequently authorized. Real Calendar/email actions and real payments remain separately gated.

Executed commands: `.venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests` (328 passed,101.860s; `artifacts/phase16/release-backend.txt`); frontend `npm.cmd test` (31 passed; `verified-frontend.txt`), `npm.cmd run lint -- --fix`, `npm.cmd run typecheck`, `npm.cmd run build`; Docker production-auth frontend build and backend image build with redacted Gitleaks; `python scripts/check_source.py` (236 files,0 failures); network-disabled redacted source scan (434 non-ignored files,2.61MB,no leaks). Logs are ignored under `artifacts/phase16`. These results do not certify legal compliance, live voice, provider billing or physical devices.

Owner/external gates: scoped public staging browser approval is pending after automatic review rejected inspection outside the prior local synthetic scope; actual iOS/Android and screen-reader access are unavailable; English live reschedule/mail receipt, actual reminder delivery, human-heard voice and real billing-provider certification remain unverified. No unexecuted check is PASS.


## Local browser integration checkpoint

Approved local Phase15 Synthetic Workspace, 320px Chromium viewport: Health Center failure exposed a missing default clock; fixed to reuse billing/runtime clock and covered by a new regression. Full backend328 tests pass in101.860s. Health loads in Bulgarian; Usage loads without alerts, switches to English, menu expands/closes and route focus moves to main. Document scrollWidth305 equals clientWidth305. Main content initially started817.4px below the top; measured mobile menu fix places it244.4px below the top, and route navigation focuses it. This is local synthetic geometry/keyboard evidence, not physical-device/screen-reader or final public browser acceptance. Captures: artifacts/phase16/browser/local-health-320.png and local-usage-320.png; earlier health capture is the before image. No real conversation or callback was inspected.
