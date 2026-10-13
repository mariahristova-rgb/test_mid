# Documented competitor UX benchmark

Primary official sources inspected13October2026. Documentation research only:no paid accounts,live product testing,mobile/a11y certification or design/branding copying. D=documented in selected sources,P=partially documented,N=not established by these sources; Ndoes not mean the product lacks the capability. Vendor documentation is not an Ontelyx test result.

| Product / documented pattern | Why useful / Ontelyx applicability | Existing Ontelyx / gap / priority |
|---|---|---|
| IntercomFin: reusable question groups,batch evaluation,response feedback and source/guidance review before rollout. [Batch Test](https://www.intercom.com/help/en/articles/10521711-batch-test-fin-ai-agent); [deployment/preview](https://www.intercom.com/help/en/articles/8286630-deploy-fin-ai-agent-over-chat) | Keep test set,configuration and feedback together; distinguish evaluation from controlled rollout | Existing UXdraft/receipts/corpus/Quality review; representative business-hour cases and actionable inline feedback missing,P0 |
| TidioLyro: guidance sections for communication/handoff with adjacent preview; knowledge managed separately. Guidance is not permission to callActions. [Guidance](https://help.tidio.com/hc/en-us/articles/20810956911004-Lyro-Guidance); [knowledge sources](https://help.tidio.com/hc/en-us/articles/14543666652316-Data-sources-Lyro-s-knowledge-base) | Separate tone/approved knowledge/action permission; test as owner edits | Existing FAQ/instructions/tools; limited side-by-side safe preview and friction on invalid setup,P0/P1 |
| Retell: separates text playground/graded simulation/batch from real browser-audio/phone tests. CustomLLMagents have different supported test modes. [Testing overview](https://docs.retellai.com/test/test-overview); [simulation](https://docs.retellai.com/test/llm-simulation-testing) | Truthful method/state labels and saved regressions; audio only after actual model/device access | Existing mock/voice fixtures; real voice preview/status/latency not accepted,P0. Adopt testing distinction only,no Retell integration/paid service |
| ZendeskAI Agents: fictional multi-turn scenario simulator/results isEAP; no-knowledge and escalation branches distinguish fallback. [SimulatorEAP](https://support.zendesk.com/hc/en-us/articles/11126903515034-Using-the-conversation-simulator-to-test-your-AI-agents-EAP); [knowledge reply](https://support.zendesk.com/hc/en-us/articles/10448933203994-Customizing-the-Knowledge-reply-in-an-AI-agent-with-agentic-AI) | Label simulation scope; actionable missing knowledge/failure branch instead of generic success | Existing safe disposable previews,FAQ/handoff/operations; interactive owner scenario/recovery coverage incomplete,P0/P1 |
| Lindy: current official entry docs describe connected task context,review/continuation,managed memory and choice of changes requiring approval. [Current docs](https://docs.lindy.ai/) | Make context/control and consequential-action approval visible | Existing explicit tools/approvals; customer continuity proof missing,P0. Cached Academyaction-confirmation page now redirects,so exact older UI not asserted current |

## Selected-source journey coverage

| Journey | Fin | Lyro | Retell | Zendesk | Lindy | Ontelyx evidence/gap |
|---|---|---|---|---|---|---|
| First-owner onboarding | P | P | P | P | P | Guided steps exist; invalid-valid-hours preview blocks publication,P0 |
| Knowledge setup | D | D | P | D | P | Approved bilingualFAQ exists; knowledge import/coverage source review incomplete |
| Personality/style | D | D | P | P | N | Instructions exist; preview/clear control interaction,P1 |
| Voice setup | P | N | D | P | N | Self-hosted adapters exist; actual preview/model/heard gate open |
| Testing/preview | D | D | D | D(EAP) | P | Mockreceipts exist; representative scenarios need fix,P0 |
| Booking/scheduling | N | N | N | N | P | Real adapter/offline lifecycle; no competitor parity asserted |
| Human escalation | D | D | P | D | P | Queued request/takeover exist; live availability not certified |
| Verified customer cross-channel continuity | N | N | N | N | N | BLOCKED; shared context references do not prove verified identity |
| Analytics | P | P | P | P | P | Exact ledger/operations exist; costs/SLO/cohort denominators incomplete |
| Error recovery | D | P | D | D | N | Safe unknown/retry exists; owner form/recovery UX needs testing |
| Mobile usability | N | N | N | N | N | Source/VM and historical local320px only; no current device evidence |
| Accessibility | N | N | N | N | N | No comparative audited conformance; Ontelyxkeyboard/device/screenreader gates remain |

Sources do not establish that all vendors support BG,commercially-cleared self-hosted speech,booking ownership or equivalent privacy. Do not copy their hosted/public-key/storage choices into Ontelyx; preserve scoped iframe/server credentials,verified identity and no mandatory paid inference. No usability or conversion numbers inferred from screenshots/marketing.
