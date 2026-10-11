# Phase 12 acceptance — DEMO_BLOCKED

**HTTP_JOURNEY_PASS_BROWSER_UNVERIFIED. WIDGET_DEMO_READY is not claimed.** Cloud production and telephone readiness remain separate blocked gates.

## Fresh verification

| Check | Result / evidence |
|---|---|
| Backend baseline before Phase 12 | 262 tests passed, 77.879 s; artifacts/phase12-baseline-backend.txt |
| Final complete backend regression | 276 tests passed, 113.357 s; artifacts/phase12-final-regression.txt |
| Final widget follow-up | 14 tests passed, 11.899 s; artifacts/phase12-final-widget-tests.txt |
| Frontend source/security/localization tests | 14 passed; artifacts/phase12-final-frontend-tests.txt |
| Typecheck / lint / production build | PASS; artifacts/phase12-final-frontend-{typecheck,lint,build}.txt |
| Source boundary check | 190 source/config files, zero failures; artifacts/phase12-source-check.txt |
| Offline redacted secret scan | No leaks in approximately 2.07 MB; artifacts/phase12-secret-scan-final.txt |
| BG/EN sandbox booking, rejection, ambiguity, FAQ | Eight PASS receipts in the new fictional tenant |
| Real separate-origin nonce file verification | PASS against nginx example site, not mocked fetch |
| Separate-origin widget HTTP booking | PASS twice with persisted appointments and agent handoffs |
| Duplicate confirmation | PASS; only two appointments |
| Public ID / visitor bearer on staff APIs | Rejected in API tests |
| Origin/CORS/CSP, ticket replay/expiry, revoke, quotas, changed payload replay | API/unit PASS; not a browser security certification |
| Unpublish and compatible rollback | PASS on local HTTP deployment |
| Permanent revoke / clear after revoke / corrected-network domain proof / one-use ticket / private proxy paths / gzip / single-script sample | PASS on a separate disposable HTTP integration; artifacts/phase12-http-security.json |
| Original demo clinic | Seven bookings and assistant projection hashes unchanged |
| Desktop/mobile installation and keyboard/screen reader | BLOCKED / awaiting human review |
| Human visual dashboard review | Owner answered Not yet checked |
| Browser Web Vitals / slow network / real CMS | NOT MEASURED |
| Browser voice / telephone acceptance | UNAVAILABLE / BLOCKED |

The local app is at 3017, widget at 3020, and external sample at 3021. These are different origins despite sharing loopback. Only `/widget/` routes are proxied on 3020. Existing speech/model/SIP services were not restarted. The sample uses exactly one generated embed script.

New tenant: `e5de6cb1-6d8d-4726-aa06-a4641bae9b0a`, Fictional Widget Clinic. Booking IDs `bca4c9e6-d0a0-483b-a8ea-d7c5a10e1414` and `0a012b55-d1b2-4d20-bbb9-e559df7576aa`. Date 12 October 2026, 15:00 Иван Иванов and 16:00 Jane Smith, Europe/Sofia. The authenticated dashboard APIs show the bookings and traces; no visual screenshot proof is claimed. Calendar, LLM, verification email and billing are explicitly MOCK.

## Failures retained

The first script incorrectly read receipt `status` instead of `verdict`; corrected and resumed the same tenant. English FAQ failed language detection; a regression fix and retest passed. An immediate post-restart request got HTTP 502 during warm-up, then succeeded after healthy startup. A spaced ISO date in the mock booking request was unsupported; the runtime requested a date and created no booking. The successful run used the existing localized date formats. Its earlier conversation remains visible. Repeating the consumed domain challenge returned 409; resume now recognizes verified state. The initial internal sample-site network allowed backend ownership verification but refused Windows loopback access. Moving the sample to a separate publish bridge fixed actual site HTTP access, with port binding still loopback-only. No failed attempt is represented as a passing call or browser check.

## Commands and scope

Run `.venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests -q`; from semantic_os/frontend run `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`. Run `scripts/check_source.py`, stage-source scanner, and the redacted secret scan separately. `scripts/phase12_local_journey.py prepare` creates or resumes the fictional tenant; `verify` performs the authorized synthetic bookings once and preserves evidence. Do not point this script at real business tenants.

## Remaining acceptance

Open http://127.0.0.1:3021 and verify one-script launcher/iframe/bootstrap/chat, locale switching, consent and privacy controls, BG/EN confirmed booking, error/retry, keyboard/focus, screen reader status, narrow viewport and an actual mobile browser. Inspect the selected fictional tenant dashboard. Test installation and lifecycle UI, unauthorized hosts and offline reconnection in real browsers. Record measured desktop/mobile/slow-network performance and XSS/postMessage behavior. Current source-contract checks do not substitute for these E2E/a11y tests.

Prior browser security denial is respected; alternate browser/screenshot automation was not used. Human reports can add acceptance evidence, but Not yet checked supplies no acceptance. Missing voice, real calendar, outbound channels, verified public signup and payment remain labeled. No paid cloud resources/public deployment/production migration/commit/push occurred in Phase 12.
