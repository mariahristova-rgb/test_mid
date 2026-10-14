# Increment 2 final evidence matrix

Historical Increment 2 checkpoint. The subsequent explicitly approved Increment 3 closes the selectable lifecycle/provider and scoped local mobile/keyboard/manual AT gates. See [Increment 3 evidence](INCREMENT3_FINAL_EVIDENCE_MATRIX.md); historical NOT TESTED/BLOCKED results below are not rewritten as if they passed at this checkpoint. Overall Phase 24 and production GO remain unclaimed.

14 October 2026. Focusedlocalpatchimplemented following concretefile-levelplananduser“continue”. **FullIncrement2 NO-GO;Phase24completion,UXGOandproductionGOarenotclaimed.** All remaining external/voice/identity/API/schema/financial/protectedbranch gatespreserved.

| Gate | Result | Actual evidence |
|---|---|---|
| Increment1criticalregressions | PASS synthetic | independent27entrytests,representativeschedules |
| Narrowfocusedonboarding/validation/help | PASS automated+boundedbrowser |39frontendtests,compile;businesssubheadings/sevensteps,noautosave |
| Save/conflict/reload | PASS observed | twoeditors409,retainedvalues,disabledreload,explicitdiscardthenrevision4 |
| Current/stalesimulationclarity | PASS observed |8BG/ENbooking/negative/FAQcases;dirtyrequiredrowsstale;timestamp/revision/hash |
| Bookingavailability/idempotency/privacy/tenant | PASS synthetic |28UX/full356backend;realavailabilityanduxsimulatorunchanged |
| Existingcorpus/schema/source/build/website | PASS |46corpus/schema1–5/244source0failures/78website;fullcommandsinregressionreport |
| Reschedule/cancel/out-of-hours/unsupported/unknownpreviewselection | BLOCKED | newpublicscenarioenumnotapproved;servicefixturetestsnotUIcapability |
| Eightbusinessstages/multipleservices/fullreadinessdiagnostics | PARTIAL | existingsevenpersistedsteps/singleservicepreserved;optionalnotmade mandatory |
| Duplicate/conflictingFAQ | NOT TESTED / gap | noautomaticsemanticconflictdetectorornewserverrule |
| Mobile/AT/fullkeyboard/ownercomprehension | NOT TESTED in full | boundedentry320observation;updated390requestactual1265,overrideineffective;SaveTabtransitiononly |
| Actualactivation/live/providers/customerdata | NOT AUTHORIZED | mock,in-memory,loopbackonly;noactualbooking/email/call/model |

## Exact modified source/test files

- semantic_os/frontend/src/views/SetupView.vue
- semantic_os/frontend/src/services/setupValidation.mjs
- semantic_os/frontend/src/locales/bg-BG.json
- semantic_os/frontend/src/locales/en-US.json
- semantic_os/frontend/tests/setup-validation.test.mjs
- semantic_os/frontend/tests/workspace.test.mjs
- semantic_os/backend/tests/test_ux.py
- semantic_os/config/phase17_evaluations.json

TenrequiredIncrement2documentsarein docs/phase24. No backendruntime/calendar/RunInput/schema/evaluatorrunner/websiteCSSsourceedited. Browserfixture/build/logsareignoredlocalartifacts,reuseexistingcreate_app/Store/ProviderRegistry/Vite;notanewtestframeworkorproductionentrypoint.

## Compatibility / rollback

Vue/FastAPIcontractsandDraftInputstep0–6,RunInputenum,schema5 unchanged. Realcalendaravailability,bookingownership,idempotency,uncertaintyandconsentretentionunchanged. Existingreceiptfieldsareused;nosyntheticactivationinferredfromPASS. Source-sectionlabelsareexplicitsettingsmapping,not inventedknowledgeprovenance.

Rollbackonlythisfeature-branchincrementcommitwith`git revert <increment2-commit>`afterdiffreview;rerunregressioncommands. Preserveprior873f381previewfix;noDBdownmigration/providercleanupneeded. No publicdeploymentorprotectedmerge/push. No deployedDR/restoreclaim. Finalcommit(ifcreated)reportedseparatelytoavoidself-referentialhash. Fixtureandtemporarytabsstopped/closed;in-memorysyntheticeditsdisappearwithfixtureprocess.

The16acceptancejourneysarepartlyvalidated:service/window/FAQ/save/error/stale/conflicthaveboundedbrowserobservations;closed/occupied/tenant negativesautomated;provideruncertainpreviewblocked;fullnew-ownerBG/ENcompletionandkeyboard/mobilemanualjourneysnotfullytested. No fabricatedusabilitytime/scores. StopbeforedeferredIncrement3contracts/runtime.


## Sixteen requested acceptance journeys

| Journey | Steps and expected behavior | Actual result / evidence | Verdict |
|---|---|---|---|
| 1. New BG owner completes setup | Create draft, configure all steps, review without activation | BG draft/business/FAQ and preview observed; all seven steps not completed | NOT TESTED in full |
| 2. New EN owner completes setup | Repeat full journey in English | English controls, recovery and status observed; full fresh owner journey not completed | NOT TESTED in full |
| 3. Service and hours | Save service with 10:00–10:30 window, 30-minute duration | Saved revision 2 and successful booking cases in both languages | PASS bounded browser |
| 4. FAQ edit and preview | Add paired synthetic FAQ, save and run required tests | BG/EN FAQ PASS; exact saved English answer displayed | PASS bounded browser |
| 5. Save and resume incomplete draft | Save edited service, reload, sign in and reopen | Entry build restored revision 3, service and hours; process restart not tested | PASS page reload only |
| 6. Correct validation error | Clear Name, Save, restore and Continue | Entry build focused invalid field and then Business heading; native helper regression passes | PASS bounded browser/unit |
| 7. Booking within hours | Run booking in BG/EN against saved window | Required suite PASS with one disposable booking | PASS synthetic/browser |
| 8. Closed day | Configure closed date and test refusal/representative slot | Existing closed-day/DST tests pass; separate browser closed-day interaction not run | PASS automated only |
| 9. Fully occupied schedule | Seed occupied selected slot or block all preview dates | Existing occupied cases and new fully blocked window return truthful outcomes | PASS automated only |
| 10. 30-minute working window | 10:00–10:30 with 30-minute service | BG/EN booking PASS | PASS synthetic/browser |
| 11. Edit after successful preview | Change Service after eight passing tests | All required result rows marked stale; activation disabled | PASS observed |
| 12. Recognize stale evidence | Inspect latest result and readiness after edit | Both UI languages label earlier configuration and require save/rerun | PASS observed |
| 13. Simulated provider failure | Select uncertain-write/provider-failure preview | Unsupported in existing public scenario enum; underlying service tests are not UI acceptance | BLOCKED |
| 14. Unauthorized tenant access | Try other tenant draft/preview with synthetic principal | Existing tenant/RBAC tests pass in targeted and full suite | PASS automated only |
| 15. Keyboard only | Complete all steps using keyboard, errors and preview | Enter Save and Save-to-Tab-to-Continue verified; full journey not run | NOT TESTED in full |
| 16. Narrow mobile viewport | Run full flow at 320/390 px | Entry 320 request measured 305 without overflow; updated 390 request remained 1265 | NOT TESTED for updated full flow |

No completion times or owner comprehension scores were measured. These verdicts distinguish component/service evidence from full rendered journeys.
