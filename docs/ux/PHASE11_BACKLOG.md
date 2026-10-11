# Prioritized backlog and status

10 October 2026. Owner approved incremental redesign and missing Phase 10 P0.

| Priority / item | Impact / effort / dependency | Current acceptance |
|---|---|---|
| P0 honest counts/provider scope | High / small / existing metadata | Implemented; no automatic Live Verified state |
| P0 draft/setup/isolated BG/EN testing | High / large / existing orchestration | API regressions pass; resume/revision/side-effect checks present; human journey pending |
| P0 debugger and booking links | High / medium / recorded events | Metadata privacy/ownership/order tests pass; real visual operator review pending |
| P0 keyboard/focus/bilingual barriers | High / medium / Vue native controls | Source and locale coverage pass; assistive-technology/zoom/mobile acceptance pending |
| P1 grouped navigation/Assistant Studio | Medium / medium / owner approval | Implemented progressive/read-only sections and explicit draft entry; visual navigation validation pending |
| P1 inbox performance | High / medium / measured N+1 | Query/payload gains measured; legacy full-list latency not improved |
| P1 frontend delivery | Medium / medium / baseline build | Route splitting measured; total JS grows; Web Vitals unmeasured |
| P1 human takeover | High / small / existing RBAC/control | Preserved with explicit paused state and refreshed selected metadata; observed operator rehearsal pending |
| P2 richer analytics/custom layouts | Unknown / large / instrumentation and usability evidence | Deferred; no fabricated percentiles, unread state, charts or identity merging |

Remaining: observed nontechnical dry-run; browser desktop/tablet/mobile and screen-reader checks; representative call-timeline/production Auth0 timing; real provider connectivity receipts; richer configurable regression scenarios; safe version rollback with business-policy history; multi-service scheduling. Existing tenant registration remains in the SaaS onboarding route. The wizard reuses the tenant's initial assistant rather than duplicating signup infrastructure.
