# Phase 14 audit and implementation plan — 10 October 2026

Both remotes are readable. Actual website remains Vue 3/TypeScript/Vite/Netlify; test_mid is Vue/Vite with FastAPI and tenant-scoped SQLite. Separate branches are `codex/phase14-concierge` in both repositories. Existing Phase 11–13 work is preserved; website base includes local commit 5e262c0. No production branches are modified.

## Observed facts

- Earlier connection refusal was a local nginx directory redirect to container port 8080. `semantic_os/deploy/nginx.ontelyx-review.conf` now uses relative redirects; both `/ai-assistant` URL forms returned HTTP 200.
- `artifacts/phase13b/ontelyx/.env.local` is explicitly a local build pointing at 127.0.0.1:3020. That output must never be deployed publicly. `scripts/public-config.ts` already rejects HTTP loopback in Netlify builds, but requires stronger hosted endpoint checks and distinct local/staging configuration.
- Existing iframe (`semantic_os/widget/frame.html`, frame.js/frame.css/catalog.js) is generic, has persistent mock/voice disclosures, and prioritizes free text. Website entry (`src/components/AiAssistantEntry.vue`, `src/views/AiAssistantView.vue`) has limited mobile sizing and no full-screen background-scroll/back-button handling.
- Google OAuth, live FreeBusy/event tools, verified management, Gmail delivery and concierge leads are missing. Existing tools/calendar are mock. ReceptionistAgent and TaskExecutionAgent in booking.py, ToolRegistry and existing durable Store/jobs/secrets must be reused.
- Browser automation was previously denied; no alternate browser/screenshot bypass is permitted. Requested width screenshots, mobile keyboard, iOS/Android, screen-reader and Web Vitals measurements remain blocked/unobserved. Code/HTTP/unit checks are not substitutes.
- Owner selected the primary calendar for mariya.manolova92@gmail.com and needs OAuth client setup instructions. No client/consent is present. Live Calendar/Gmail acceptance is blocked until owner setup and separately approved live tests. No calendar write/email is authorized by a screenshot or account address.

## Exact ownership and plan

test_mid: `assistant/google_workspace.py` for encrypted admin OAuth and authenticated adapters; `assistant/concierge.py` for policy, verified ownership, requests/reminders and existing two-agent tool handoff; `assistant/concierge_api.py` for v1 scoped routes; existing widget.py for capability/config integration; widget assets for localized action-first forms/calendar selector; backend tests for OAuth/replay/isolation/buffers/DST/idempotency/reminders. Existing admin frontend gets an admin-only Google configuration screen. No proprietary runtime dependencies.

Website checkout: `artifacts/phase13b/ontelyx/src/components/AiAssistantEntry.vue`, AiAssistantView.vue, assistant-labels.ts for native concierge entry and mobile focus/scroll/back behavior; scripts/public-config.ts and staging env example for HTTPS-only public endpoints; tests and website docs. No business logic or Google tokens in the website.

Shared: versioned availability/booking/management/request contract, public ID + short-lived widget session, locale/correlation/idempotency semantics. Preserve existing chat and phone behavior. Initial policy: Mon–Fri 10:00–19:00 Europe/Sofia, 30 minutes, 15-minute buffer, cutoff 2026-12-31, all editable for later years.

Implement and validate offline first, expose accurate unavailable states, then obtain owner OAuth action. User authorized commit/push both feature branches **after completion**; live deployment and real event/email tests still require separate explicit authorization. Dependencies from uncommitted prior test_mid phases must be included in its reviewed checkpoint so the pushed backend builds independently.
