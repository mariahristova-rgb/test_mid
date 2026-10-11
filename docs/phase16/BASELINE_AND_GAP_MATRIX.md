# Phase 16 baseline and gap matrix

Audit: 11 October 2026, 20:37–20:41 Europe/Sofia. This is discovery evidence, not Phase 16 completion. Paths below are relative to the named repository. Estimates are engineering effort ranges, not delivery promises; external acceptance waiting time is excluded.

## Repository state

Both worktrees were clean at entry. `test_mid` inherited local Phase 15 commits `6f6237c`, `7b2a5d3` on top of `4ddf9ee`; `ontelyx` inherited `f8999d7` on top of `40894dc`. Both now use separate `codex/phase16-saas-operations` branches. No push, merge, cloud provisioning or live message occurred in this audit. The website checkout is `artifacts/phase13b/ontelyx` under the root repository's ignored artifacts directory; it remains an independent Git repository and build pipeline.

Reviewed `docs/product/PHASE15_RELEASE_DECISION.md`, `PHASE15_PRODUCT_AUDIT.md`, performance reports, website `docs/product/PHASE15_WEBSITE_AUDIT.md`, router, inbox, onboarding, billing, widget, backup and orchestration boundaries. Some early Phase 15 report paragraphs are superseded by their latest checkpoint: scoped synthetic browser acceptance passed; current hosting ceiling is €2/week, preferably free. No public staging host exists. Phase 15 P1/P2 remain incomplete.

## Requirement mapping

| Phase 16 requirement / owner journey | Decision and exact implementation boundary | Main risk / effort | Acceptance evidence and remaining gap |
| --- | --- | --- | --- |
| 1 Discovery, gaps and baseline | KEEP architecture; ADD this report and `EXECUTION_PLAN.md` | Misstating inherited results; 0.5–1 day | Fresh suites/builds below; provider receipts are inherited, not rerun |
| 2 Business-first navigation and BG/EN states | IMPROVE `semantic_os/frontend/src/services/navigation.mjs`, `App.vue`, `assets/main.css`, `services/i18n.ts` | RBAC/focus regression; 2–4 days | Existing groups preserve routes; Leads/Analytics/Team entries are not implemented; no dead links should be added |
| 3 Resumable onboarding and publishing blockers | KEEP `backend/assistant/billing.py`, `ux.py`, `widget.py`; IMPROVE `frontend/src/views/{SaaSView,SetupView,WidgetView}.vue` | Stale test evidence/domain proof; 3–5 days | Draft/test/readiness and real nonce-domain installation APIs exist; full cross-screen progress and adoption events missing |
| 4 Operator inbox and business records | KEEP `backend/assistant/inbox_queue.py`, `messaging.py`, `orchestration.py`, `frontend/src/components/InboxQueue.vue`; IMPROVE `views/WorkspaceView.vue` | Reply identity, AI resume and retention; 3–5 days | Assignment, CAS state, notes, human provenance and synthetic browser takeover pass; priority/SLA/unread/resolution taxonomy and unified leads UI missing |
| 4 Google lifecycle, invitation and reminders | KEEP `backend/assistant/{concierge,google_workspace,jobs,booking}.py`; BLOCKED full live certification | Real external effects; 1–3 days plus owner/provider acceptance | Approved BG move/cancel and EN create/cancel receipts; BG mail received. EN move, human EN receipt, actual reminder delivery and uncertain-send operational acceptance remain open |
| 5 Assistant Health and reviewed Quality Coach | ADD projections using `backend/assistant/ux.py`, `observability.py`, `store.py` and existing `components/ConversationDebugger.vue`, `views/SetupView.vue` | Sensitive trace exposure/stale evidence; 4–6 days | Existing diagnostics/test receipts; no consolidated Health Center or reviewable coach yet; no automatic live mutation permitted |
| 6 Consent-aware business funnel | ADD bounded aggregate projections beside `widget.py`, `concierge.py`, `privacy.py`; existing `store.py` remains the only database | Consent, misleading inferred outcomes; 3–5 days | No measured adoption/conversion/revenue baseline; existing booking records include cancelled fixtures and cannot be counted as conversions |
| 7 Usage and cost center | KEEP `backend/assistant/{entitlements,billing,saas_domain,saas_api}.py`, `frontend/src/views/SaaSView.vue`, `services/money.mjs`; IMPROVE reporting and thresholds | Duplicate billing/unit mixing; 3–5 days | Existing append-only usage, reservations, plan snapshots, minor-unit invoice math, one configurable warning threshold. Per-dimension history and multi-threshold alerts need implementation; LLM token summary currently reports unreported_by_mock |
| 8 Measured capacity/performance | KEEP `scripts/benchmark_phase11.py`, `frontend/src/services/localPerformance.mjs`, lazy `router/index.ts`; IMPROVE measured bottlenecks | Synthetic workload mistaken for capacity; 2–4 days | Fresh disposable API baseline below; slow-network/device/vitals/provider/voice measurements remain open |
| 9 Operations and recovery | KEEP `backend/assistant/{observability,jobs,backup,saas_api}.py`, `scripts/backup_assistant.py`; IMPROVE operator projections/runbooks | Unsafe replay or restored provider jobs; 2–4 days | Existing correlation, redaction, dead letters and encrypted isolated restore tests pass; observed SLO/error-budget and deployed restore drill absent |
| 10 Security/privacy/governance | KEEP `backend/assistant/{security,privacy,tools,widget,google_workspace}.py`; IMPROVE tests and retention boundaries | Tenant escape/credentials/public invention retrieval; 2–4 days | Isolation/privacy tests and source boundary pass; no legal compliance certification; no proprietary semantic runtime added |
| 11 Mobile public website and widget | KEEP website `src/{config.ts,components/AiAssistantEntry.vue,views/AiAssistantView.vue,assistant-contract.ts,assistant-labels.ts}` and backend `widget.py`; IMPROVE only verified integration gaps | Publishing local origins; 1–3 days plus device/DNS access | Website public-config canaries pass. Local build is preview-only. Public HTTPS integration, iOS Safari, Android Chrome, screen reader and 200% zoom remain unverified |
| 12 Test/release strategy | KEEP existing suites; ADD targeted tests per workstream | Claiming mock tests as live certification; ongoing | Current deterministic results below. Scoped local synthetic browser permission persists; real-account callback/private conversations excluded |
| 13 Delivery order | KEEP A→H order; approval before major changes | Skipping Phase 15 gates; ongoing | Critical live/device gates tracked independently; no external side effects without specific approval |
| 14 Reports | ADD `docs/phase16/*` incrementally with evidence | Empty reports mistaken for completion; ongoing | Two discovery deliverables created now; later acceptance documents follow executed workstreams |
| 15 Final acceptance | BLOCKED | Untested provider/device/public deployment; external | No PILOT_READY or PRODUCTION_READY claim. Current scope is tested local foundation only |

Existing host integration is shared and must not be replaced by a second assistant implementation.

## Capability confidence

- MOCK: payment checkout/invoices, deterministic calendar fixtures and isolated Test Studio; these are not provider billing certification.
- CONNECTED / limited LIVE-VERIFIED: owner-authorized primary Google Calendar/Gmail receipts from Phase 15; only the explicitly named operations passed, not all lifecycle/reminder journeys.
- TESTED local: two-agent BG/EN chat, permission checks, persistent conversations, widget origin/domain guards, inbox takeover, billing math and isolated restore fixtures.
- NOT CERTIFIED: voice audibility/acoustic consent, public HTTPS staging, PSTN/WhatsApp/SMS, real payments, device accessibility and production capacity.

No measured per-tenant compute allocation, production support incident rate, onboarding completion/drop-off, customer attendance or revenue dataset exists in this audit. Report these as unavailable, never zero. A self-hosted token count does not establish a currency charge.

## Fresh execution evidence

Commands run from `test_mid` unless noted; logs are ignored under `artifacts/phase16` and contain no intentionally copied credentials:

```
.venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests
.venv/Scripts/python.exe scripts/check_source.py
.venv/Scripts/python.exe scripts/benchmark_phase11.py --samples 20 --output artifacts/phase16/api-baseline.json
# semantic_os/frontend:
npm.cmd test
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
# artifacts/phase13b/ontelyx:
npm.cmd test
npm.cmd run build
npm.cmd run test:config
npm.cmd run format:check
docker ps --format '{{.Names}} {{.Status}}'
docker stats --no-stream --format '{{.Name}} {{.MemUsage}} {{.CPUPerc}}'
```

Backend: **309 passed in 102.674s**; source boundary: **227 files, 0 failures**. Frontend: **29 passed**, lint/typecheck/build pass; build includes environment-secret checks. Website: **72 Vitest + 6 Node passed**, typecheck/build/config canaries/format pass. Dependency warning: installed Starlette TestClient emits an httpx deprecation; no dependency migration undertaken during discovery. A fresh full Gitleaks/security certification has not been performed here; Phase 15's redacted scan is inherited evidence only.

Isolated recovery actually runs in `semantic_os/backend/tests/test_saas.py`: `test_backup_restore_preserves_tenant_usage_and_encrypted_credentials`, `test_on_disk_wal_backup_restores_committed_data`, and tamper/wrong-key rejection. These use disposable fixtures, not a deployed disaster-recovery rehearsal or access to real customer backups.

API measurement at **2026-10-11T17:39:31.876901Z**: single concurrency, 1,000 synthetic conversations, in-process ASGI/in-memory SQLite, mock providers, 20 samples. Assistants p50/p95/p99 **16.12/21.15/28.00 ms**; full Inbox **38.48/56.11/95.38 ms**, **207,230 bytes**; 50-row page **12.95/14.90/15.25 ms**, **10,511 bytes**. The detail fixture has no messages (2-byte response), so it is not a representative long-conversation benchmark. This is baseline only, not before/after improvement or multi-customer capacity evidence.

Docker snapshot: Qwen **2.438 GiB**, TTS **1.26 GiB**, STT **301.7 MiB**, backend **67.49 MiB**, Asterisk **50.95 MiB**; Qwen/STT/TTS/backend reported healthy. Single idle snapshot, not peak memory or a successful audible call. Two unrelated containers were active and CPU-busy; none was modified. Host competition is a measurement confounder.

## Blocking owner/external actions

Large product changes require approval of the concrete execution plan. The previously rejected VM cloud-platform OAuth scope is still pending explicit approval; Phase 16 does not grant it. No paid VM/IP/disk exists. DNS, registered Google owner-login redirect, public-host acceptance, real-device/screen-reader access, EN inbox receipt and additional named live calendar/reminder test authorization remain open. Existing unrelated cloud services and private voice ports must remain untouched.
