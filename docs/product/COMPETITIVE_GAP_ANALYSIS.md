# Competitive capability evidence — 11 October 2026

These are current official documentation reads, not authenticated hands-on UX tests. DOCUMENTED_CAPABILITY means the linked source describes it; OBSERVED_UX is reserved for an actual product interaction, and none of the vendor consoles was accessed. PROPOSED_DESIGN is our independent inference. No vendor asset, design or source was copied.

| Product | Documented capability reviewed | Observed UX | Independent gap/action |
|---|---|---|---|
| Vapi | [Logs](https://docs.vapi.ai/observability/logs/overview), [debugging](https://docs.vapi.ai/debugging), [monitoring](https://docs.vapi.ai/observability/monitoring-quickstart) describe separate traces/testing and threshold-based issues | Not observed | Reuse our traces; expose privacy-safe provider/confirmation causes and test coverage without asserting voice quality |
| Retell AI | [Simulation testing](https://docs.retellai.com/test/llm-simulation-testing) describes repeatable text tests, criteria and function mocks; text simulation is distinct from real audio. [Widget](https://docs.retellai.com/deploy/chat-widget) describes public-key embedding, configurable text/voice and optional anti-abuse controls | Not observed | Keep text/mock/live evidence separate, require privacy-reviewed regression approval, preserve short-lived scoped widget sessions |
| Voiceflow | [Behaviour](https://docs.voiceflow.com/docs/custom-llm) documents model/session/fallback configuration; [environment session API](https://docs.voiceflow.com/api-reference/session/start-session-specific-environment) scopes session keys. [2024 publishing release](https://docs.voiceflow.com/changelog?page=8) is historical publishing evidence, not proof of unchanged current UI | Not observed | Unify existing Studio/drafts/receipts and keep live environment separate from tests; current visual publishing UX not verified |
| Intercom Fin | [Reporting](https://www.intercom.com/help/en/articles/7837533-fin-ai-agent-reporting) distinguishes resolution, escalation and pending outcomes and exposes filters/definitions. [Reporting API](https://developers.intercom.com/docs/guides/reporting/ai-agent-report) documents outcome data | Not observed | Define booking/current cancellation/inquiry outcomes instead of treating persisted counts as success; link evidence and sample sizes |
| ElevenLabs Agents | [Operate](https://elevenlabs.io/docs/eleven-agents/operate/overview) documents testing/history/privacy; [analytics](https://elevenlabs.io/docs/eleven-agents/dashboard) documents agent/branch/locale dimensions, latency percentiles, errors and workflow outcome review | Not observed | Add scoped outcome projections and human-reviewed quality insights after P0 gates; avoid premature adaptive tuning |

Access date for all links: 11 October2026. Attempts to read guessed Voiceflow publishing/evaluation URLs and an alternate Retell automated-testing URL failed; no capability was inferred from those failures. Published first-value times are vendor claims, not our observed task metrics.

## Comparison coverage and uncertainty

| Dimension | Evidence in reviewed sources | Our state / priority |
|---|---|---|
| Onboarding / first-value time | Some documented setup flows; no measured participant times | Existing resumable setup; measure a consenting session, do not invent five-minute outcome |
| Agent editing / knowledge / tools | Vapi debugging, Retell function mocks, Voiceflow behaviour docs | Existing assistant/FAQ/tool contracts; unify their presentation |
| Versioning / simulations / deployment | Voiceflow environment session API and historical publishing; Retell simulation and widget | Existing drafts/immutable widget snapshots; retain rollback/receipt invalidation |
| Human takeover / conversation review | Fin escalation outcomes; Vapi logs, ElevenLabs history | Existing takeover; Phase15 queue/notes increment; browser acceptance still open |
| Analytics / voice debugging | Fin definitions, Vapi debugging, ElevenLabs percentiles/errors | Raw counts are not outcome analytics; voice quality remains an independent gate |
| Embed installation | Retell widget documentation | Existing small isolated loader; verify reachable HTTPS origins |
| Mobile / accessibility | No hands-on measurements or comprehensive conformance evidence reviewed | Unknown for vendors; test our actual widths, focus, contrast and screen readers |

PROPOSED_DESIGN: default business navigation, progressive technical disclosure, one evidence/readiness vocabulary and a human-reviewed failure-to-regression workflow. These are tailored to our existing Vue/FastAPI contracts, not reproductions of vendor layouts.
