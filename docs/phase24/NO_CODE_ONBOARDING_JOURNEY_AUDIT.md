# Increment 2 UX audit and file-level proposal

14 October 2026. Read-only application audit plus separately approved local synthetic browser acceptance. The file-level plan was presented before edits. The user subsequently instructed “continue”; the contract-preserving local changes below were implemented. Deferred public-contract/scaling/voice work remains outside approval. Preserve Vue/FastAPI, step0–6 contract, existing URLs/RBAC/calendar/schema. Do not add public scenario enum values under the current no-contract-change boundary.

## Existing journeys

All setup/preview flows reuse SetupView at /setup and /testing, starting from Assistants or saved drafts. Admin configures; admin/operator executes existing preview. App handles sign-in and tenant selection; local browser used only a new synthetic in-memory tenant.

| Flow | Existing actions/validation | Feedback/recovery | Keyboard/mobile/locales/tests |
|---|---|---|---|
| Business/service/hours | business step1; name,one service,duration,timezone,weekdays,opening interval,optional price/profile,closed dates/periods | Save/Continue native+server validation; alert; retry/edit; no autosave | labels,first-invalid focus;320px no overflow in observed view;BG/EN;Business/schedule/UX tests |
| FAQ/knowledge | use-case step0 details; add/edit/remove paired BG/EN entries | required fields/native/server; no explicit duplicate/conflict guidance | labels/collapsed reveal helper; actual FAQ keyboard/edit acceptance NOT TESTED;existing FAQ tests |
| Booking policies | duration/hours step1,allowed tools step3,channels step4 | server guards;shared-tenant activation warning | no separate concise booking summary; existing booking/privacy/idempotency suite |
| Language/behavior | use-case template/instructions step0,UI/default conversation/voice locale step2 | preserves provider settings; no live voice setup | document lang switches;BG/EN separate conversation context; observed browser language switch |
| Human escalation | EscalateToHuman tool step3,agent settings link /agents | permission intersection;existing handoff scenario | no separate no-code escalation details; availability not inferred |
| Preview | ten supported RunInput scenarios; saves dirty editable draft then isolated mock tests |PASS/FAIL/BLOCKED,response/tools/agent handoffs,revision/hash/reference/timezone; no-slot message |6requiredBG/EN passed browser; FAQ/handoff existing tests; audio interruption honestly BLOCKED |
| Readiness/activation | required test receipts+existing reasons/channels | draft/tested/published separated;explicit confirmation+server publish gates | stale receipt marked after edit and after save/reload;activation never clicked |
| Save/resume | saved list,step persistence,revision conflict,dirty route guard,beforeunload | success notice,409reload action,discardlocalchanges | saved values restored after reload/relogin;reload saved can discard local edits and needs explicit warning;no autosave |

Current seven steps are use-case,business,language,tools,channels,test,review. Proposed eight-section business sequence cannot become eight persisted steps without changing current DraftInput step0–6. Keep persisted sequence and use plain business subsections/summary. Single-service model is supported; multiple services/split schedule engine are not silently promised.

## Proposed runtime scope for review

| Priority | Exact file changes | Tests / risk |
|---|---|---|
| P0 | semantic_os/frontend/src/views/SetupView.vue: business-oriented subsection headings/help,progress text using existing seven steps; optional FAQ empty state; explicit save-before-preview text; receipt timestamp/config revision and relevant configuration section label; actionable readiness next steps; keep existing activation controls | frontend unit/helper tests+synthetic CUA; risk misrepresenting validation progress: never equate visited steps with valid configuration |
| P0 | same SetupView: show stale required evidence as stale/currentness warning, not six apparently current PASS rows under dirty form; explicit unsaved-change warning before Reload saved; preserve server409 handling and edits on failures | replay concurrent/dirty/save/resume tests; no silent overwrite; no autosave claim |
| P0 | semantic_os/frontend/src/services/setupValidation.mjs and .d.mts only if reproduced field-feedback gap requires it: preserve existing aria-describedby tokens while adding/removing setup error association | tests/setup-validation.test.mjs; no server validation replacement |
| P0 | semantic_os/frontend/src/locales/bg-BG.json,en-US.json: matching plain-language help/next-action labels; preserve CRLF | tests/workspace.test.mjs localized evidence assertions |
| P0 | semantic_os/backend/tests/test_ux.py: additional narrow-window,afternoon,weekday,split-via-blocked-period,fully-blocked14days,legacy/replay/tenant malformed-config acceptance using existing simulator | no backend availability or public API change |
| P1 | semantic_os/config/phase17_evaluations.json: register added reviewed tests in same corpus; scripts/evaluate_phase17.py unchanged unless existing runner demonstrably requires it | corpus validation/evaluation; no parallel test framework |
| P1 | existing assets/main.css only if browser reveals specific touch/overflow/focus defect |320/390desktop,zoom/reduced-motion geometry checks; no broad styling rewrite |

Missing preview reschedule/cancel/out-of-hours/unsupported/provider-unknown scenarios are documented as gaps. Existing backend lifecycle tests are evidence for their services, not a visible Test Studio capability. Do not relabel another scenario to simulate them. New RunInput values/public contracts require separate review and are outside this proposed contract-preserving patch. Source attribution currently supports configuration section/FAQ configuration; no invented citations or hidden reasoning.

FAQ duplicate/conflict advice may be informational only unless a reproducible ambiguity demonstrates need for a separately reviewed server invariant. Optional FAQs/contact/price/escalation must not block configurations where existing contracts allow omission. No crawling, paid ingestion or third-party analytics.

## Acceptance and rollback

Before testing: zero real/provider writes,zero tenant leaks/duplicate bookings;100%selected critical synthetic assertions;invalid focus targets correct field;saved values/revision survive page reload after sign-in;dirty results never labeled current;320/390px observed views no horizontal overflow. Human comprehension/time-to-complete thresholds remain unset until actual tester protocol is reviewed; do not invent scores. Screen reader/physicaldevice NOT TESTED unless actually executed.

After approved changes run targeted UX/booking/calendar/frontend helpers,BG/EN/negative tests,existing full backend/frontend/website suites,versioned corpus,source/secret/build/migrations checks; record commands/verdicts in required reports. Compile/Node success is not browser acceptance. Existing browser scope now covers named synthetic local setup/preview/keyboard checks only.

Rollback proposed source increment via reviewed feature-branch git revert; no schema/downmigration/provider cleanup. Remove only new synthetic artifacts/services if needed; no realDB/cache/customer changes. Preserve prior873f381 correction and all consent/uncertainty/ownership gates. No push,main merge,voice,mic,deployment,paidwork,DR/scaling/identity scope. Only the supported focused changes were made; assets/main.css, backend simulator/availability and evaluator runner did not require edits. See final matrix for actual changed files.
