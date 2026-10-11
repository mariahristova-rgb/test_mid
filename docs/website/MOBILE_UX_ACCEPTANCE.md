# Mobile acceptance — not yet certified

| Environment/check | Status |
|---|---|
| 320 / 360 / 390 / 428 / 768 / 1024 / 1440 CSS px screenshots | BLOCKED: prior browser automation denial; none fabricated |
| Portrait/landscape, software keyboard, zoom 200% | NOT OBSERVED |
| iOS Safari / Android Chrome | NOT RUN |
| Keyboard / screen reader / WCAG 2.2 AA | Source foundations and DOM unit checks only; actual acceptance pending |
| Scroll lock/restore and prior overflow state | Mock-DOM website unit test PASS |
| Cookiebot launcher suppression / restoration | Documented event handling + mocked-event unit test PASS |
| Safe-area, dvh/visualViewport, fixed composer, 44px controls | IMPLEMENTED_UNVERIFIED |
| LCP / INP / CLS / slow 4G / mobile memory | NOT MEASURED |

Manual review must verify both languages at every listed width, orientation and keyboard state; scrolling the conversation must not scroll the background or clip the composer. Check Escape/back/close focus restoration, repeated opens, language choice, consent banner overlap, offline/timeout/idempotent retry, expiry and management-link forms. Record observed defects separately from proposed changes. Unit jsdom/VM state checks are not browser rendering or screenshots.

Prior UI tooling denial was respected. No alternate browser engine, screenshots through shell or raw-CDP bypass was used. Voice remains unavailable. Do not claim mobile readiness from CSS or successful HTTP.
