# Increment 3 — regression and acceptance evidence

14 October 2026. All application actions used a named synthetic loopback fixture, in-memory Store and mock providers. No owner Calendar/Gmail connection, customer database, model cache, speech model, microphone, PBX, billing expansion or deployment was used.

## Automated commands

From test_mid:

- `.venv/Scripts/python.exe -m unittest semantic_os.backend.tests.test_ux`: 30 PASS, 4.414s, artifacts/phase24/increment3-targeted.txt. The full suite subsequently includes the stronger unsupported-fallback assertion.
- `.venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests`: 358 PASS, 46.073s, increment3-backend.txt.
- `.venv/Scripts/python.exe scripts/evaluate_phase17.py --output artifacts/phase24/increment3-evaluations.json`: corpus 1.5.0, 48/48 PASS. Mock tokens remain unmeasured; pilot_ready=false.
- `.venv/Scripts/python.exe scripts/check_migrations.py --output artifacts/phase24/increment3-migrations.json`: versions 1–5, integrity, foreign keys and data preservation PASS.
- `.venv/Scripts/python.exe scripts/check_source.py`: 244 source/config files, zero failures.
- `node semantic_os/security/scan-secrets.mjs semantic_os/backend semantic_os/frontend/src semantic_os/config scripts docs/phase24`: 345-file final local comparison PASS; no fresh Gitleaks or hosted CI attestation is claimed.
- `git -c core.whitespace=cr-at-eol diff --check`: PASS after removing one trailing space; existing locale CRLF preserved.

In semantic_os/frontend: `npm run test` 39 PASS; `npm run typecheck`, `npm run lint`, `npm run build` PASS. Logs: increment3-frontend.txt and increment3-build.txt. ESLint formatted only the modified SetupView. Final preview-label edits were followed by these checks again.

In artifacts/phase13b/ontelyx: `npm run test` 72 Vitest + 6 Node PASS; `npm run test:config`, `npm run build`, `npm run format:check` PASS. Website source/worktree unchanged. Logs: increment3-website.txt and increment3-website-build.txt.

## Scenario assertions and browser results

Seven new scenarios pass in both languages in unit acceptance and actual In-app Browser runs (14 cases), with a further seven Bulgarian runs at 320 px. Reschedule/cancel verify approval gating, ownership of the synthetic conversation and approval replay with exactly one management tool execution. Provider cases verify one attempt and zero confirmed local bookings. Both primary tenants' appointments, jobs, conversations, messages, assistants, agents and usage tables remain unchanged by the simulator. Existing revision, tenant and API authorization tests remain in the full suite.

Permission negatives: absent assistant or executor management permissions produce BLOCKED/tool_denied before creating a prerequisite booking. A seven-day schedule without holidays produces BLOCKED/preview_no_closed_day. No configuration is silently changed to manufacture a passing negative test.

Browser evidence: increment3-browser-scenarios.json, increment3-bg-mobile-results.json and the saved JPEG screenshots. English onboarding was performed using keyboard inputs and Tab navigation through all seven steps, including an invalid Name correction, service edit, lifecycle permissions, review and required BG/EN tests. Bulgarian onboarding also reached all seven steps and ran the six required tests at 320 px. Activation was never clicked. Saved draft resumed after reload/sign-in.

## Actual defects corrected and limitations

Initial new unsupported English question resolved to bg-BG; the test reproduced it, and binding the explicit selected preview locale corrected it. Existing booking/language-switch detection tests remain unchanged. Measured metadata contrast was 4.344:1; focus against white was 2.542:1. Narrow CSS changes produce 6.917:1 and 6.702:1 respectively in built browser styles. The lower metadata color change is scoped to bubbles.

The prior 390 px failure was a browser targeting issue: the viewport capability had been applied while another tab was selected. This turn measured actual innerWidth=390 on the active tab, then clientWidth=scrollWidth=375 with its scrollbar; at 320, clientWidth=scrollWidth=305. Do not reinterpret the earlier failed attempt as a historical PASS.

Browser zoom shortcuts did not change observable scale; this was not marked as an automated zoom PASS. The user explicitly confirmed the real screen-reader required-field announcement and usability at 200% zoom. These are user-attested manual PASS, not agent-run AT measurements. Exact AT/version was not supplied. Current CSS has zero animated/transitioning visible main elements, and the existing reduced-motion rule is preserved; OS preference switching was not exercised. No physical mobile/touch hardware certification is claimed.

Read-only DOM attempts for getAnimations/parseFloat were unsupported by the browser proxy. Supported computed-style observations were used instead, without injecting CSS or bypassing browser control. Initial keyboard login appended to a prefilled username; selecting/replacing the existing values corrected the test procedure. No software was installed. Existing Starlette/httpx deprecation warning remains.

A final denied-tool reproduction exposed a misleading unknown-provider response when no provider attempt had occurred. The simulator now reports the actual localized permission error, with no invented booking status; BG/EN failure/unknown prerequisite regressions pass. The final full-suite run was repeated after this correction; the final result is 358 PASS in 46.073s, and the refreshed corpus is 48/48 PASS.
