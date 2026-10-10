# Phase 10 baseline — Stage A

Checked 10 October 2026; source checkpoint 873c4e1. Stage A only: no application changes or deployment. Evidence is source inspection and regression checks, not an observed usability study.

## Route inventory

All fourteen routes appear together in App.vue navigation. Router inventory: dashboard, assistants, agents, inbox, calls, channels, appointments, integrations, settings (WorkspaceView); onboarding, billing, usage, operations, administration (SaaSView). Root and unknown routes redirect to dashboard. Existing routes will remain compatible.

| Area | Verified implementation | UX gap / evidence |
|---|---|---|
| Sign in | Local demo exchange; production Auth0 support; memory-only bearer | No measured first-run task success; App.vue |
| Tenant onboarding | Organization, locale, timezone, plan, verification | Separate from assistant configuration; SaaSView.vue |
| Assistant | Instructions, languages, channels, voice settings, active/disabled | No draft/published version boundary; domain.py AssistantConfig |
| Voice editor | Mock/Twilio and mock/Azure selects | Deployed Asterisk/local speech absent from choices; WorkspaceView lines 179–181. Saving deserves regression protection |
| Agents/tools | Two agent forms and allowed-tool checkboxes | Business purpose and effective assistant/agent permission intersection not explained |
| Inbox | Filters, messages, human takeover/resume/reply | Test conversations use real conversation endpoints; no safe isolated studio |
| Calls | Events, agent/tool executions, linked appointment data | Activity is presented in separate groups, not a unified stage timeline |
| Appointments | Tenant-scoped persisted records | No complete bidirectional detail navigation journey |
| Channels | Connection controls and messaging foundations | A configured adapter or static mock banner is insufficient evidence of delivery |
| Operations | Tenant aggregates and bounded content-free voice traces | Count/mean/max cannot supply median/p95; trace expires on restart |
| Localization | BG/EN JSON, independent persisted UI locale, timezone-aware Intl | Raw API errors and provider enum choices need human-readable localized mapping |
| Security | Server tenant scoping and role checks | Call activity currently requires configure permission; operator access must be designed explicitly, not weakened globally |

Source paths are under semantic_os/frontend/src and semantic_os/backend/assistant. Existing SQLite migration version is 5. Backend contracts require both supported locales; setup must explain this rather than offer a single-locale selection that fails validation.

## Actual integration and release baseline

Phase 8 original calls produced proposals without booking. Phase 8B selected synthetic affirmative SIP workflows persisted three appointments; this is synthetic test evidence. Phase 9 is DEMO_BLOCKED: human BG/EN listening and visual dashboard acceptance absent, acoustic question-to-affirmative failure unresolved, Bulgarian fixed-date speech probes failed. Optional keypad guard is tested source, inactive and undeployed. See ../demo/PHASE9_READINESS.md and PHASE9_SAFETY_PREPARATION.md; older opening summaries in Phase 8B are superseded by their later receipts, not silently discarded.

Web Chat and mock calendar persistence are implemented. Self-hosted Qwen/STT/TTS and local SIP have prior test evidence, not complete live acceptance. Email/WhatsApp/SMS connections for the demo are NOT_CONFIGURED; mock adapter tests do not establish external delivery. Billing/payment foundations use mocks. No proprietary semantic runtime is required by this design.

## Accessibility and evidence limits

Source shows wrapped form labels, alert/status regions, visible focus styling and mobile media queries. App.vue has no skip-to-main link; fourteen links create a long keyboard path. No route-change focus management is evident. Long voice forms expose infrastructure before task testing. Contrast, keyboard execution, screen-reader behavior, Cyrillic overflow and actual mobile rendering remain unverified, not WCAG certified.

Screenshots unavailable: the existing local browser inspection was denied by browser security. No alternate capture method was used. No authenticated competitor dashboards were accessed. Baseline click count, completion time and time-to-first-success are unknown. Human dry-run remains unverified.

Current flow: sign in → onboarding/settings → assistants → agents → channels → inbox or SIP harness → calls → appointments → operations. This describes routes, not a measured click count.
