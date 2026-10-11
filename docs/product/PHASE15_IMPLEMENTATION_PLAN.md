# Phase 15 incremental implementation plan

11 October 2026. Branches in both repositories: `codex/phase15-product-experience`. Baselines: test_mid `4ddf9ee`, ontelyx `40894dc`. Owner approved progressive navigation grouping and one named reschedule/cancel test. No Phase 15 push, merge or public deployment is authorized.

| Gap | Evidence | File-level change | Gate |
|---|---|---|---|
| Business navigation mixes operational screens | `semantic_os/frontend/src/router/index.ts`, `App.vue` | Group existing routes, preserve URLs and role filtering; localized group labels | Owner approved incremental grouping |
| Google lifecycle only BG create accepted | `concierge.py`, latest Phase 14 receipts | Execute approved signed-link reschedule/cancel; inspect jobs, provider event and appointment | Owner approved 14 October 15:00→16:00→cancel, same recipient |
| Inbox lacks assignment/status/notes | `messaging.py`, `WorkspaceView.vue`, `ConversationDebugger.vue` | Extend existing conversation metadata/API with validated queue transitions and redacted audited notes; add filters to existing inbox | Synthetic tests and browser journey before acceptance |
| No Leads & Requests operator view | `concierge_api.py` already exposes tenant requests | Add filtered view using current store, assignment/follow-up metadata and permission checks | No second inbox/store |
| No shared readiness center | `ux.py` readiness, Google status, provider descriptors | `product.py` projection over existing receipts/config; `ProductView.vue` health cards | Never upgrade connected to LIVE_VERIFIED |
| Studio/test evidence fragmented | `SetupView.vue`, `AssistantStudio.vue`, `ux.py` | Existing configure/connect/test/review/publish sections, stale receipt gates, regression proposal metadata | Preserve actual publishing controls |
| Business KPIs are raw counts | `WorkspaceView.vue` dashboard | Tenant-scoped metadata projection for outcomes and observed funnel stages; unavailable stages shown unknown | No invented widget-open events, no raw analytics bodies |
| Quality Coach missing | Existing diagnostic events and tool failures | Bounded metadata-only deterministic insights; human-approved regression drafts | No auto training/publishing |
| Public deployment connectivity unknown | `ontelyx/src/config.ts`, build guards, iframe readiness | Audit deployed HTML/public build targets and refine localized offline recovery | Reachable HTTPS widget origin required; never expose Windows |
| Mobile/a11y and performance incomplete | Only Watch Demo browser checks are verified | Real browser width/keyboard journeys; audit tokens and focus; record local measurements separately from representative Web Vitals | No iOS/Android or p75 claims without devices/samples |

P0-A: baseline, current official competitor documentation, observed owner/visitor flows and gap matrix. P0-B: focused connectivity/locale/mobile/inbox and calendar lifecycle repairs. P1-A/B/C proceed only after P0 acceptance; P2 industry presets and advanced diagrams remain gated. Keep small local commits with tests, no destructive migrations, no inference/model replacement.

External gates remain: English live booking, actual inbox receipt and reminder delivery; representative network/device performance; human acoustic voice consent/audibility; public HTTPS staging configuration. Read-only runtime audit is authorized; further live sends/Calendar writes require named approval.
