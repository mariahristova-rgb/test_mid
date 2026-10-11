# Phase 13B acceptance — browser review pending

**Local HTTP integration passes; browser/staging acceptance is not complete.** No production-readiness, voice-readiness or live-website parity claim is made.

| Check | Actual result |
|---|---|
| Repository read access / actual framework | PASS; both remotes readable; website Vue 3/TS/Vite, test_mid Vue/FastAPI |
| Unchanged website baseline | Build/typecheck, Prettier and 47 Vitest + 6 Node tests passed |
| Integrated website | Build/typecheck, Prettier, 58 Vitest + 6 Node tests passed |
| Public configuration canaries | PASS; five allowlisted public fields, private/VITE secret canaries absent |
| test_mid backend full regression | 278 tests passed, 91.677 s; artifacts/phase13b/backend-full-last.txt |
| Focused widget/onboarding tests | 35 passed, 13.763 s |
| test_mid frontend | 19 tests, lint, typecheck and build PASS |
| Shared loader protocol | Mock-DOM unit coverage: lazy iframe, exact source/origin/schema, one ticket, bound readiness and teardown; not browser E2E |
| Dedicated tenant sandbox | Twelve BG/EN booking/rejection/ambiguity/FAQ/switch/handoff cases PASS |
| Actual website-origin ownership | PASS against the local actual Vue build's nonce file |
| Public FAQ / BG/EN booking | PASS via real HTTP and existing agents; two confirmed synthetic bookings persisted |
| Duplicate confirmation / language switching | PASS; no extra booking |
| Unapproved origin / unpublish / rollback | PASS on local HTTP |
| Original clinic | Seven bookings and assistant configuration hashes unchanged |
| Website route / slash redirect | Fixed; both forms return HTTP 200 at host port 5173 |
| Human browser/mobile/keyboard review | Initial owner report: connection refused; corrected redirect, recheck pending |
| Visual dashboard review | Pending |
| Browser voice | Disabled; no mic controls/capture; existing private media transport is not a public voice certification |
| LCP / INP / CLS / slow-network profiles | NOT MEASURED; browser inspection blocked |
| Public Netlify deploy / HTTPS staging / production merge | NOT PERFORMED |

LLM, calendar, billing and verification email are MOCK for this demo. Agents, permission checks, tenant ownership, persistence and confirmation are the existing runtime. Contact uses an existing website link/form; no automatic message is sent. Only approved public product/demo information is configured. No proprietary semantic runtime or confidential invention documents are connected.

## Failures retained

The appearance regression test found existing widget edits attempted to rewrite immutable assistant_id even without changing it; fixed at the service boundary, retaining Store's binding protections. Initial full test discovery rejected a relative fixture import; corrected to an absolute import and reran the real command. An immediate post-restart login got 502 before backend readiness, then passed. The owner found a real review URL failure: nginx redirected the directory route to internal port 8080. `absolute_redirect off` fixed it; slash/non-slash HTTP checks now pass. These failures are not hidden by unit-only passes.

## Evidence and outstanding gate

Evidence is under artifacts/phase13b: baseline/final website build/tests/format/config logs, backend-full-last.txt, test_mid frontend logs, demo-state.json, demo-http-results.txt, clinic-before/after.json and performance.json. Build artifact tests preserve existing public media, policy metadata, contact form and Netlify behavior; they do not prove every live interaction.

Human review must use http://127.0.0.1:5173/ai-assistant/ and the homepage floating entry. Check Bulgarian/English, iframe/presentation, keyboard close/focus, narrow/mobile viewport, screen reader state, privacy/consent, expired/offline retry and persisted dashboard results. Browser automation denial is respected; no alternate screenshots/browser engine bypass was used. Dedicated HTTPS staging, actual browser security/performance and public visitor voice remain separate gates.
