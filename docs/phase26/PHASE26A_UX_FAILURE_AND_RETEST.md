# UX failure and retest
The latest user manual screen-reader/200% zoom answer was negative: “no they are not”. Preserve FAIL / AWAITING_HUMAN_VERIFICATION. No reader/browser or exact failed control was specified; do not infer a PASS from an older Phase24 attestation.

Reconciliation restores accessible setup validation from Phase24 alongside five-stage navigation, locale race protection and current control/layout fixes. The existing targeted test verifies invalid Save/Continue opens hidden FAQ and focuses the first invalid field before a request. Both locales and route mapping pass unit tests.

Fresh browser restart attempt: the isolated fixture on 127.0.0.1:8020 was initially unreachable from the browser; browser reported connection refused. Prior pre-merge screenshots/layout receipts are historical only and are not merged-build acceptance. Host socket inspection subsequently confirmed a loopback listener on port 8020; the existing browser tab remained on a cached connection-error document. Fresh browser retest remains required. No security policy bypass was attempted.

Required retest: BG/EN new/save/resume drafts; empty required field and keyboard focus; locale switch without losing unsaved work; 320/390/768/desktop setup, billing and connector views; real Narrator/NVDA announcements and 200% zoom. Capture reader/browser, actual result and screenshot before changing manual status.
