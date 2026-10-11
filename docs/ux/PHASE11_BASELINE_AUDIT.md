# Phase 11 baseline audit

Checked 10 October 2026. Work restricted to test_mid. Stage 10 was audit/proposal only; the owner explicitly approved the incremental redesign and missing P0 implementation in this phase.

Source baseline: 213e0ce on main. Vue 3/Vite/FastAPI/SQLite; the frontend AGENTS.md Next.js guide does not describe the installed Vue application and its referenced Next directory is absent. Existing components/infrastructure are retained.

| Evidence reference | Verified baseline finding | Implemented response |
|---|---|---|
| router/index.ts and App.vue | Fourteen peer links; no skip link or route focus management | Nine primary entries, technical routes in Advanced; skip link and route focus |
| WorkspaceView.load | Ten requests on every workspace route, including unrelated contacts/messages | Route-specific read plans and cancellation of superseded route loads |
| AssistantConfig / voice selects | Asterisk/local STT/TTS omitted; latency input capped below backend range | Complete existing provider enums; 120000 ms contract limit |
| Dashboard badge | WORKING applied to every stored count | Stored-record label; no success-rate interpretation |
| Phase 10 docs and source | No wizard, isolated studio or unified debugger | Draft workflow, disposable simulations, evidence-only diagnostics |
| messaging_api.inbox | Per-conversation message/contact lookups | One SQL enrichment query, tenant-safe filters and 50-row UI pages |
| API benchmark | 1005 read statements for 1000-conversation inbox | Four total request reads including authentication; one inbox statement |
| Phase 9 readiness | Consent/audio/date/human gates unresolved | Explicit blocked voice status; no SIP promotion from mock tests |

Screenshots at desktop/tablet/mobile remain unavailable: existing browser security denied local inspection. No alternate browser, shell capture or indirect UI automation was used. Reproducible references: `/assistants`, `/setup`, `/testing`, `/inbox?conversation=<owned-id>`, `/calls`, `/appointments?conversation=<owned-id>`, `/operations` on local port 3017. Source references are not visual QA.

Baseline click count, task time, actual layout defects, Web Vitals, hydration/render counts and browser memory growth are unknown. There is no verified observed nontechnical dry-run. Existing Phase 8/8B/9 reports remain blocking evidence; three synthetic successful calls were not human-accepted live calls.
