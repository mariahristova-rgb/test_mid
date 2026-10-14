# UX failure and retest
The latest user manual screen-reader/200% zoom answer was negative: “no they are not”. Preserve FAIL / AWAITING_HUMAN_VERIFICATION. No reader/browser or exact failed control was specified; do not infer a PASS from an older Phase24 attestation.

Reconciliation restores accessible setup validation from Phase24 alongside five-stage navigation, locale race protection and current control/layout fixes. The existing targeted test verifies invalid Save/Continue opens hidden FAQ and focuses the first invalid field before a request. Both locales and route mapping pass unit tests.

Fresh browser restart attempt: the isolated fixture on 127.0.0.1:8020 was initially unreachable from the browser; browser reported connection refused. Prior pre-merge screenshots/layout receipts are historical only and are not merged-build acceptance. Host socket inspection subsequently confirmed a loopback listener on port 8020; the existing browser tab remained on a cached connection-error document. Fresh browser retest remains required. No security policy bypass was attempted.

Required retest: BG/EN new/save/resume drafts; empty required field and keyboard focus; locale switch without losing unsaved work; 320/390/768/desktop setup, billing and connector views; real Narrator/NVDA announcements and 200% zoom. Capture reader/browser, actual result and screenshot before changing manual status.

## Follow-up on 2026-10-14
Fresh merged build became reachable after restarting the disposable loopback fixture. Observed login profile reconciliation to English; BG switch preserved unsaved synthetic business name. Save and Continue persisted draft revisions 1 and 2; next-step heading received focus. Setup widths 320/390/768/1280 showed client/scroll widths 305/305, 375/375, 753/753 and 1265/1265. Visible buttons were at least 44px tall. These are browser DOM measurements, not screen-reader or zoom acceptance.

Human retest again FAILED; the owner clarified: error is not read aloud. Reproduced a regression test for rendered feedback before focus; initial result 2 PASS/1 FAIL because native reportValidity competed with the custom region. Correction waits for Vue rendering before focus, keeps a persistent atomic alert region, refreshes repeated error announcements and removes the competing popup. Targeted result 3/3 PASS; frontend full suite 46 PASS. Human reader retest of the corrected build remains required; no manual PASS claimed.

Second browser reproduction found that :invalid selected the invalid fieldset, leaving focus on Continue. Selector now targets input/select/textarea only. Corrected browser retest confirms the input is active with aria-invalid=true and aria-describedby=setup-error; localized atomic alert is present. Screenshot: ignored artifacts/product-ux/phase26a-feedback.png. Real screen-reader and zoom retest remains pending.

Owner corrected-build retest again reports nothing is spoken. Manual result remains FAIL; reader/browser version is still unspecified. DOM input-focus and atomic alert observations cannot supersede this result. Billing widths 320/390/768/1280 had no page overflow; visible buttons minimum44px, text-decoration none. No billing action submitted.
