# Competitive evidence review

Checked 10 October 2026. All findings below are documentation-based; no authenticated product behavior, screenshots or customer metrics were observed. Strengths are design interpretations. Limitations describe documented constraints or the limits of this review, not universal product judgments. No competitor assets or layouts are copied.

| Product / official evidence | Documented flow, CTA and navigation | Strength, limitation and original lesson |
|---|---|---|
| [Vapi debugging](https://docs.vapi.ai/debugging), [call logs](https://docs.vapi.ai/observability/logs/call-logs) | Select assistant, Talk to Assistant, inspect Logs → Calls and call details. Logging and recording/transcript settings are separate. | Immediate testing near configuration; call-focused diagnosis. Full onboarding/publishing sequence not established by these pages. Lesson: Test Assistant CTA plus independent privacy controls. |
| [Retell simulation](https://docs.retellai.com/test/llm-simulation-testing), [documentation index](https://docs.retellai.com/llms.txt) | Agent → Simulation → Test Cases; create scenario, criteria, variables/mocks, Run Test, Batch Testing History. Docs separate Build, Test, Deploy, Data, Monitor. | Repeatable criteria and run history. Text simulation does not validate audio; custom LLM unsupported in this simulation, unmocked functions can reach real endpoints, MCP ignores mocks. Lesson: enforce isolation for every tool and show audio coverage separately. |
| [Voiceflow behavior](https://docs.voiceflow.com/docs/custom-llm), [regression test](https://www.voiceflow.com/docs/cookbook/test-a-conversation-flow.md) | Behavior settings govern model/session/fallback; test scripted turns and checks, run and inspect results. Documentation groups agent configuration and API tests. | Contextual settings and repeatable checks. Actual dashboard primary CTA and full onboarding not observed; legacy Prompts CMS should not guide new designs. Lesson: contextual configuration plus outcome assertions, no new visual builder. |
| [Intercom email deployment](https://www.intercom.com/help/en/articles/9356221-deploy-fin-ai-agent-over-email), [procedure troubleshooting](https://www.intercom.com/help/en/articles/13704396-troubleshooting-fin-procedures-and-data-connectors) | Train content, Test questions/review responses, Deploy → Email audience and handover, Set Fin Live, Analyze. Procedure handoff routes to team/workflow. | Explicit audience and handover before deployment. Live internal email testing is still live and billable. Lesson: separate isolated preview from actual activation; make human takeover visible. |
| [ElevenLabs quickstart](https://elevenlabs.io/docs/eleven-agents/quickstart), [agent testing](https://elevenlabs.io/docs/eleven-agents/customization/agent-testing), [analytics](https://elevenlabs.io/docs/eleven-agents/dashboard) | Create agent via dashboard/API, test dashboard/widget. Testing includes simulation, next reply and tool call; conversations can become tests. Analytics filters include language and time. | Different test scopes and outcome context. Documentation is not proof of Bulgarian voice quality in this deployment. Lesson: separate language/provider capability from actual synthesis acceptance; sanitized failure replay. |
| [Bland pathways](https://docs.bland.ai/tutorials/pathways), [version reference index](https://docs.bland.ai/llms.txt) | Pathway nodes/edges define call behavior; version APIs support staging/production promotion and pathway chat history. Documented pathway authoring, not an observed dashboard navigation audit. | Explicit workflow and version boundaries. Detailed onboarding CTA/call outcome dashboard usability unverified here. Lesson: immutable configuration identity on tests and promotion; read-only orchestration diagram instead of builder. |

## Feature evidence matrix

D = documented in cited sources; U = not established by this review. U does not mean absent.

| Pattern | Vapi | Retell | Voiceflow | Fin | ElevenLabs | Bland | test_mid baseline |
|---|---|---|---|---|---|---|---|
| Nearby test action | D | D | D | D | D | U | No isolated studio |
| Scripted regression | U | D | D | D (question tests) | D | U | Developer tests |
| Operational call diagnosis | D | D (index) | U | U | D | U | Grouped activity |
| Human handoff context | U | D (index) | U | D | U | D | Takeover/resume |
| Explicit version promotion | U | D (index) | U | U | U | D | Missing |
| Language analytics | U | U | U | U | D | U | Coverage incomplete |

Decision: adopt test-before-activation, outcome-focused diagnostics and explicit evidence scope. Do not adopt managed providers, pricing, sample analytics, or distinctive editor layouts.
