# Phase 14 results — IMPLEMENTED, LIVE ACCEPTANCE BLOCKED

Phase 14 is **not complete**. Owner OAuth/client setup, explicitly approved live Calendar/Gmail tests, HTTPS staging and actual browser/mobile acceptance remain open. The user's completion-conditioned commit/push is therefore pending, not silently omitted. Neither production branch is modified; no public deployment, Google event, live email, infrastructure purchase or agent login to Google occurred.

## Actual verification

| Check | Evidence/result |
|---|---|
| Full backend | 296 passed, 117.782 s; artifacts/phase14/backend-final-complete.txt |
| Google/public API focused contracts | 18 passed, 1.814 s; offline httpx/TestClient fixtures, not the owner's account |
| test_mid frontend | 19 tests; lint/typecheck/build PASS; widget module syntax checks PASS |
| Actual website | 64 Vitest + 6 Node tests, build/typecheck, format and private-canary checks PASS |
| Source boundary | 205 source/config files, zero failures; source-boundary.txt |
| Offline secret scans | Root source/docs: no leaks (~2.33 MB); website source: no leaks; redacted network-disabled scans |
| Local HTTP | Website, widget loader and Google admin HTTP 200; local-final-state.json |
| Existing clinic | Seven bookings and identical booking/config hashes; clinic-before/final.json |
| New concierge | Published dedicated tenant a7cfa147-0ded-41a5-a0f1-69b717e9ece8; primary calendar selected; zero Google connections, live authorization false, zero real bookings |
| Real FreeBusy / event / mail / inbox | NOT RUN: owner credentials/consent and explicit named live-test authorization missing |
| 320–1440px / iOS / Android / keyboard / screen reader / Web Vitals | Not observed; browser tooling blocked, mock-DOM foundations only |

Tests cover encrypted OAuth storage, browser state binding/PKCE/replay, expected-account rejection, refresh/revoke, permissions, tenant/locale separation, request idempotency/retention, buffers/cutoff/DST/2027 policy, email proof, signed ownership/tamper/expiry/recovery, exact owned-event exclusion, conditional update/cancel, reminder cancellation and uncertain Gmail non-replay. Google adapters are real API implementations exercised with offline transports. The application does not substitute mock availability for disconnected Google.

## Failures retained

An initial fixture omitted the required assistant name; corrected before API tests passed. Refactoring bounded email work initially left loop-only continue statements in a helper; corrected and reran tests. One ESLint invocation used the wrong working directory; the actual frontend lint command then passed. The secret scanner falsely classified a synthetic test invocation as a key assignment; made fixture values unmistakably fake and formatted the computed idempotency-key argument separately, without suppressing the rule. The previous website connection refusal was traced to a redirect to internal port 8080 and remains fixed. No failure is presented as a successful live test.

## Measured performance and limits

Phase 13 baseline website entry: 137287 bytes / 51546 Python gzip bytes. Phase 14 measured local entry: 138617 / 51904 bytes (+1330 raw / +358 gzip). Shared loader: 5710 / 2128 gzip bytes, under the enforced 4096 gzip budget. The new concierge form/management modules load with the isolated iframe; no STT/TTS/models or new large SDK enter the host page.

Twenty sequential loopback urllib GET samples: website p50 31.76/p95 46.39 ms; loader 15.69/34.26 ms; admin 8.77/11.50 ms. These are actual HTTP/body measurements, not rendering, hydration, slow 4G, mobile memory or LCP/INP/CLS. Real calendar lookup and chat/Google latency remain unmeasured. See artifacts/phase14/local-final-state.json.

## Required owner actions and dependency order

1. Follow GOOGLE_OAUTH_SETUP.md; select **Ontelyx AI Concierge** in http://127.0.0.1:3017/google. Configure a Web client and connect Calendar/Gmail separately as mariya.manolova92@gmail.com. Keep operations off.
2. Supply approved public HTTPS staging widget/site origins; no visitor-localhost or Windows public exposure.
3. Explicitly authorize a named live test with meeting times/attendee and email recipients. Then enable the owner operations switch and verify actual Google event IDs, ownership, updates/cancel, single email/inbox delivery and same-day reminders. Do not treat a connected account or selected email as blanket test authorization.
4. Review local/staging BG/EN welcome/actions, widths, orientation, keyboard/scroll/back/focus, privacy/expiry/retry, metrics and dashboard outcomes. No browser bypass is used.
5. When completion gates pass, commit/push the two feature branches as requested. Backend contract/widget assets must be released before the website build; include its prior uncommitted Phase 11–13 prerequisites so test_mid builds independently. No direct production push, merge or live deployment without separate approval.

Remaining operational limits: one-process SQLite/account lock, external-calendar race reconciliation, uncertain write/send recovery, public edge CAPTCHA/abuse hardening, Google consent verification/testing expiry, complete business/Google/backups retention review and real-device acceptance. Voice remains unavailable. No production-ready claim is made.

## Google connection verification — 11 October 2026

Owner consent connected Calendar to Ontelyx AI Concierge. Enabled Calendar and Gmail APIs in the owner project. A real primary-calendar read returned HTTP 200, owner access and Europe/Sofia. No event or email was created. Gmail consent was recorded under SmileCare rather than Concierge; Concierge Gmail remains disconnected. Corrected demo re-login to preserve the selected session organization, validating access via bootstrap and falling back only on forbidden/not-found. Frontend typecheck, 19 tests and build passed. Gmail delivery and full live journey remain unverified.

### OAuth status after corrected tenant-specific authorization

On 11 October 2026, both Calendar and Gmail are connected to Ontelyx AI Concierge. Live Calendar primary metadata read returned HTTP 200, owner access, Europe/Sofia. Gmail token is available and includes gmail.send. No token values were logged. Email delivery, booking lifecycle and reminder acceptance have not been exercised; live operations remain off. Tenant-link regression tests pass (3), and the frontend Docker build/typecheck/lint passed.

### Approved live Bulgarian booking — 11 October 2026

Owner approved attendee mariya.manolova92@gmail.com and Wednesday 14 October 2026, 15:00–15:30 Europe/Sofia, then supplied the emailed verification code. Public scoped Web Chat actions reused Receptionist and Executor handoff, real FreeBusy and Calendar insertion. Booking 53e2ffc5-7296-4fb6-b61f-71d177a11d9f-booking persisted once; replay reported duplicate with exactly one matching dashboard appointment. Gmail verification and management jobs are sent; human inbox receipt remains pending. Reminder job is pending for 14 October 08:00 Sofia, not tested. Live operations were enabled only for the approved test and restored off; the scheduled reminder cannot send while that authorization remains off. No reschedule/cancel, English live workflow or full mobile acceptance was performed. Evidence: artifacts/phase14/live-booking-result.json.
