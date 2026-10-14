# Increment 2 local synthetic browser entry checks

14 October 2026. User explicitly approved local synthetic setup/preview/keyboard browser checks. Used computer-use/CUA In-app Browser only at127.0.0.1:8019, Phase24 Synthetic Workspace, fresh in-memory database/mock registry. No existing customer DB,Google callbacks,live providers,models or activation inspected. No screen reader certification.

Predetermined checks: no lost saved edits,no stale evidence labeled current,invalid focus target correct,explicit simulated/not-activated status,zero external effects. No completion-time/usability scores measured.

| Check | Actual steps/result | Verdict |
|---|---|---|
| Native validation | create synthetic draft;clear required Name;Save:alert+native required message;active INPUT aria-invalid=true,describedby setup-error | PASS observed |
| Continue focus | correct Name;Continue:savedrevision1,business heading focused | PASS observed |
| Narrow booking window |10:00–10:30,30-minute service;Save via Enter;Run6requiredBG/ENtests:allPASS,revision2/current,notactivated | PASS observed |
| Stale edit evidence | edit Service;latest receipt says earlierconfiguration;activationdisabled;readinesssummarydraft | PASS observed;oldrequiredrowsstillshowPASS,clarity gap |
| Locale | switchUItoBG;documentlangbg-BG;receiptconversationremainsEnglishexplicitly | PASS observed |
| Save/resume | saveeditedservice revision3;reload requires demo relogin;select saved draft/Open;service and10:00–10:30persist;revision2receiptstillstale | PASS acrosspage reload;processrestartNOTTESTED in-memoryfixture |
| Narrow viewport |320x720override:documentclientWidth305,scrollWidth305;BGbusinesscontrolsvisible/wrap | PASS measured view;wholeflowNOTTESTED |
| Focus order | Tab fromSave movesContinue;visible focusoutline in screenshot | PASS one transition;fullkeyboard-onlyjourneyNOTTESTED |
| Screenreader/contrast/touch/textzoom/reducedmotion | source labels/lang/focus/reducedmotion exist;noactualAT/contrast/zoom measurements | NOT TESTED |
| FAQedit/providerfailure/newownerend-to-end | not exercised in thisbrowserentrycheck | NOT TESTED |

Screenshots were displayed by CUA for resumed BG setup and320pxfocus; no saved PNG artifact is claimed. AX/DOM snapshots and focus/geometry observations are in tool outputs. A locator getByLabel for saved draft failed; fresh DOM showed combobox and role-based selection succeeded. No app failure inferred from locator error.

Reset viewport override after testing. Close temporary tab and stop fixture; no synthetic activation. This is bounded acceptance of existing Increment1 behavior, not all16Increment2scenarios or production usability. Runtime proposal awaits review in NO_CODE_ONBOARDING_JOURNEY_AUDIT.md. Other required final reports will be produced from actual approved implementation/results, not filled with future PASS assertions.


## Updated implementation acceptance

New Bulgarian synthetic draft,paired BG/ENFAQ,10:00–10:30 schedule:8 required cases (booking,rejection,ambiguity,FAQ in both languages) PASS in actual browser. FAQ reply matches saved synthetic answer; receipt labels FAQ config section explicitly and does not invent external attribution. Service edit makes all readiness rows stale in BG and EN rather than displaying current PASS.

Two synthetic editors: second savesrevision4;first staleeditor Save returns409 and retains “Synthetic unsaved older editor”; reloadbutton disabled until discardcheckbox checked. After explicitconfirmation,revision4/newerservice loaded. Alert receives focus. No backend/provider changes to achieve this.

Updated responsive attempt: requested390x844, but actualDOM remained1265pxwide (scrollWidth1265). Reattempt aftervisibilityshow hadsameactualsize. **390px acceptance NOT TESTED: browser viewport override did not take effect.** Do not treat desktop no-overflow asmobilepass. Earlier actual305px/320request belongs to entrybuild. Save→Tab→Continue focus transition verified onupdateddesktop. Fullkeyboard/AT/zoom/contrast/touch/reducedmotionactualmeasurement remains NOT TESTED. Screenshots displayed; no savedPNGclaimed. Temporary testtabs closed,viewportreset,fixture stopped.

The fixture session ended between user turns; initial updated-tab navigation refused connection, then a fresh in-memory fixture was started. Error-tab binding was rejected by browserURLpolicy(data-errorpage); no bypass attempted; fresh allowedloopbacktab succeeded. Locator expecting short Reloadlabelfailed; freshDOMrevealed exactexistinglabel and recoverypassed. These tooling events are not application acceptance successes.


## Increment 3 supplemental acceptance — 14 October 2026

The active-tab 390 px and 320 px tests now have measured responsive evidence, unlike the failed Increment 2 override attempt. English keyboard navigation completed all seven setup stages, corrected the invalid Name, configured mock lifecycle permissions and ran the required bilingual preview tests. Bulgarian setup also reached Review at 320 px; all seven new BG scenarios passed there. No horizontal overflow was observed (375/375 and 305/305 client/scroll widths).

Two reproduced contrast defects were fixed and verified in built browser styles: bubble metadata 4.344 → 6.917; focus versus white 2.542 → 6.702. Other sampled text/background pairs exceeded 4.5. Current review controls have accessible labels; active button heights were 44px or 67.6px. This is geometry, not a physical touch-device test.

Manual user receipt: after being asked to verify required-field error narration with Narrator/NVDA and usability of all controls at 200% zoom, the user replied “И двете проверки минаха”. Record both as user-attested manual PASS. No exact AT/version, audio capture or independent agent AT test is claimed. Browser shortcuts alone did not produce an observable zoom change and are not the evidence for this PASS.

Current visible main elements have zero non-none CSS animations and zero nonzero transition durations. The existing reduced-motion media rule remains in source; the observed OS preference was false and preference switching was not tested. A whole-product WCAG certificate, physical-device test or conformance across every page is not claimed.

Threshold references (consulted before the contrast correction): [W3C contrast minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html), [target size minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), and [status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html). Normal-text comparison used 4.5:1; large text can use 3:1. Measured geometry is distinct from a full target-spacing or AT conformance audit.

Artifacts: increment3-browser-scenarios.json, increment3-bg-mobile-results.json, increment3-control-audit.json, increment3-contrast-results.json, increment3-final-motion-geometry.json and increment3-final-preview.jpg under artifacts/phase24. These supersede only the specified missing local checks; historical failures are retained above.
