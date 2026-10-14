# Website/mobile/accessibility matrix

13October2026. Website runtime unchanged; shared loader/Vue views reused. No public Interactive Demo restored, model bundled or production origin changed.

| Check | Verdict | Scope |
|---|---|---|
| Website tests/config canaries/typecheck/build | PASS |72Vitest+6Node, local build |
| Assistant frontend tests/typecheck/lint/build | PASS |35Node tests, local build |
| Iframe reconnect/retry/expiry/handoff/consented clear | PASS | Executed code in Node VM, not a browser |
| Loader source/origin/nonce/teardown protocol | PASS | Existing synthetic Node tests |
| Local320px/menu/focus/BG/EN | Historical PASS | Phase16 synthetic Chromium only; not re-run here |
| Public BG/EN booking/mobile/keyboard | BLOCKED | Public browser scope and live staging capability acceptance absent |
| Screen reader/physical iOS/Android/cross-browser/slow network/Web Vitals | NOT TESTED | No authorized device/assistive-tech access or measurement |

Remaining acceptance must record exact browser/device/assistive technology and test focus return,44px targets,safe areas,keyboard resize,slot clipping,loading/errors/reconnect and privacy notices. No WCAG/production certification inferred from VM tests.
