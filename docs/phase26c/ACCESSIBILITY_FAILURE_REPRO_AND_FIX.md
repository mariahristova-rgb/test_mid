# Accessibility failure record
Historical user report: after empty organization name → Continue, nothing is spoken. Reader/browser/version were not supplied. Status remains FAIL (reported) / BLOCKED manual verification; no WCAG certification.

Fresh synthetic browser repro in in-app browser on Windows, /setup at8020: New assistant → clear Organization name → Continue. Visible localized error appears; actual focused INPUT has aria-invalid=true and aria-describedby=setup-error, with the error text present. Correct name → Save succeeds and preserves form values. This verifies browser DOM/focus recovery, not audible speech. Existing setupValidation/locale tests pass. No speculative additional focus changes were made without a reproducible reader-specific failure.

Manual gate needs actual Narrator/NVDA with browser/OS versions, exact announcement transcript/focus order and real 200% text zoom. Browser resizing/DOM checks are separate evidence. No human-assisted result was available in this increment. Keep manual acceptance BLOCKED and record a later real PASS/FAIL rather than repeatedly requesting generic confirmation or overwriting the previous FAIL.
