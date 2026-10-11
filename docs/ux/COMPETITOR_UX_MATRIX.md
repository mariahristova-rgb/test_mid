# Competitor UX matrix

Checked 10 October 2026. Work restricted to test_mid. Stage 10 was audit/proposal only; the owner explicitly approved the incremental redesign and missing P0 implementation in this phase.

All evidence is official public documentation checked on 10 October 2026, not firsthand authenticated testing. Benefits/effort/risk are design judgments. No screenshots, metrics, branding or layouts are copied.

| Job | Documented pattern / evidence | Current state → response | Benefit / effort / risk |
|---|---|---|---|
| Diagnose a call | [Vapi call logs](https://docs.vapi.ai/observability/logs/call-logs): call artifacts, tools and per-turn stage latency | Grouped activity → metadata timeline and scoped trace panel | Outcome clarity / medium / avoid exposing retained content or equating packets with hearing |
| Test before activation | [Retell simulation](https://docs.retellai.com/test/llm-simulation-testing): scenarios, criteria and function mocks | Developer tests only → BG/EN saved receipts | Repeatability / high / external functions can remain live in that product; our sandbox has no live handles |
| Contextual configuration | [Voiceflow Behaviour](https://www.voiceflow.com/docs/documentation/build/behaviour): model/session/fallback and speech settings; public navigation groups Build/Deploy/Measure | Long forms → read-only sections with draft editing | Progressive disclosure / medium / FAQ is not a document knowledge base |
| Controlled handover | [Fin deployment](https://www.intercom.com/help/en/articles/9356221-deploy-fin-ai-agent-over-email): train/test/deploy, audience and handover | Existing takeover → visible AI pause and preserved controls | Operator confidence / medium / isolated tests are distinct from live delivery |
| Different test scopes | [ElevenLabs testing](https://elevenlabs.io/docs/eleven-agents/customization/agent-testing): simulation, next reply and tool tests | One undifferentiated interaction → explicit mock text scope and blocked audio | Honest coverage / medium / no Bulgarian synthesis inference |

Voiceflow's regression cookbook URL returned an internal fetch error during this phase; its accessible Behaviour page and official index were used. No unavailable page is presented as firsthand evidence. Existing Phase 10 benchmark remains historical research context.
