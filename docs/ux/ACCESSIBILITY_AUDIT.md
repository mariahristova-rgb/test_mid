# Accessibility audit — incomplete acceptance

10 October 2026. Target WCAG 2.2 AA for changed paths; no conformance certification.

Implemented: skip-to-main and route focus; visible 3 px high-contrast focus; native labeled fields and grouped legends; native validation; alert/status regions; reduced-motion override; readable metadata wrapping; checkbox-label and operational-link touch targets; tab roles/selection/panel associations with Left/Right/Home/End keyboard handlers. Mobile debugger selectors are native pressed-state buttons, not fake ARIA tabs. No custom dialog or focus trap was introduced.

Locale tests cover both resources, literal text nodes/keys and changed components, plus scenario/state labels. Contrast calculations for four changed token pairs are in artifacts/phase11-contrast.json. These do not execute keyboard or screen-reader interactions.

UNVERIFIED: desktop/tablet/mobile rendered layout, 200/400% zoom, full contrast inventory, Cyrillic overflow, keyboard-only creation/resume/diagnosis, focus after validation and actual screen-reader announcements. Browser inspection remains blocked. Source lint/unit tests do not replace Playwright/assistive-technology testing; no E2E pass or screenshot count is claimed.

Reproduce manually: tab from sign-in to skip link/navigation, use Assistant Studio arrow/Home/End keys, advance/back/save setup, verify required-field errors, switch BG/EN independently, inspect mobile debugger panels and appointment links. Report focus loss, unlabeled controls or hidden content before marking acceptance complete.
