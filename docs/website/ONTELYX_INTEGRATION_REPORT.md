# Phase 13B two-repository audit and plan — 10 October 2026

## Access and boundaries

Both GitHub repositories are readable. Website HEAD is `0d4cb4d2572bde85ef90d11ac089d93391a1d012`; test_mid remote HEAD is `213e0ce5b7b36fa8dbde5a76fdfaf91b3b66e0ed`. Existing uncommitted Phase 11/12 changes are preserved. Local branches are `codex/phase13b-website-integration` (test_mid) and `codex/phase13b-assistant-integration` (website). The isolated website checkout is `artifacts/phase13b/ontelyx`; it is an independent Git repository, ignored by test_mid. No original proprietary runtime checkout is modified.

The public live URL could not be fetched by the web tool. Source inspection establishes the integration framework/branding; no live visual parity claim is made.

| Website responsibility | Actual source |
|---|---|
| Vue 3 / TypeScript / Vite entry | src/main.ts, src/App.vue, index.html |
| Router / lazy views | src/router.ts, src/views/ |
| Navigation / layout | src/components/AppHeader.vue, AppFooter.vue |
| Design system | src/tokens.css, src/styles.css; navy #080f1c, cyan #54dde2, Segoe UI, 8px corners |
| Existing public auth | src/config.ts; public account controls paused; existing Auth0 retained |
| Public config allowlist | scripts/public-config.ts, vite.config.ts, src/env.d.ts |
| Build/test pipeline | package.json, package-lock.json; build/typecheck, Vitest + Node, Prettier; no ESLint |
| Hosting/deployment | netlify.toml; npm build → dist, SPA redirects, security headers |
| CI/CD | No repository GitHub Actions configuration found. Netlify settings/Git-trigger behavior require owner review |

Website environment fields are explicitly allowlisted; arbitrary VITE-prefixed secrets are not exported. Existing Cookiebot/auth/contact/video and semantic showcase are preserved. Website public product text is presentation only, not a semantic runtime connection.

## Implementation plan and exact paths

Website checkout:
- `src/components/AiAssistantEntry.vue`: native floating/embedded entry, loading/error/cleanup, public config only.
- `src/views/AiAssistantView.vue`, `src/assistant-labels.ts`: bilingual product/demo entry, synthetic-calendar notice and existing contact route.
- `src/App.vue`, `src/components/AppHeader.vue`, `src/router.ts`: mount entry and add lazy route without redesigning unrelated pages.
- `scripts/public-config.ts`, `src/env.d.ts`, `.env.example`: validated widget origin/public ID only.
- `tests/assistant.spec.ts`, public configuration/security artifact checks: lifecycle, language, failure, no voice activation and no secret export.
- `docs/website/*`: installation, staging and acceptance instructions.

test_mid:
- `semantic_os/widget/v1.js`, `loader.css`, `frame.js`: reuse one protocol/runtime; add embedded presentation and scoped teardown/readiness events.
- `semantic_os/backend/assistant/widget.py`, widget CSS: safe predefined Ontelyx appearance, same tenant/session/tool boundaries.
- `scripts/phase13b_ontelyx_demo.py`, `semantic_os/backend/tests/test_website_widget.py`: dedicated synthetic tenant/public FAQ configuration and HTTP security/booking checks.
- `docs/website/ONTELYX_INTEGRATION_REPORT.md`, `WEBSITE_WIDGET_ACCEPTANCE.md`, `DEPLOYMENT_INSTRUCTIONS.md`: exact results and remaining gates.

Measure unchanged website build/tests and emitted bytes before edits. Validate both builds and the actual website local HTTP origin. Browser/mobile/keyboard/Web Vitals acceptance remains blocked by the prior browser-security restriction; do not bypass it with another UI automation route. Browser voice stays unavailable until separate BG/EN speech, consent and browser transport acceptance succeeds. No paid service, public deployment, production merge or direct production push is authorized by this phase.

## Implemented and verified increment

Actual website build is served on http://127.0.0.1:5173/ai-assistant/ with both URL forms verified after the nginx redirect fix. The existing homepage gets a native floating entry; the dedicated page is lazy. No backend, SDK, model, staff credential or proprietary runtime is duplicated in the website. The iframe/agent protocol remains shared with Phase 12. Safe Ontelyx appearance preserves other tenants' default theme.

Dedicated tenant: `fbf27dbf-cd36-4409-81f6-9006ef9fb888`; public ID `wdg_11f0609ea9874a79a31a53acba378217`. Twelve sandbox cases passed. BG/EN public FAQs, two-agent confirmed synthetic bookings, duplicate prevention, explicit language switching, origin rejection, unpublish and rollback passed via real HTTP. Two appointment IDs: `f6079158-fb37-4770-8bb9-ca0f34e35724` / `6a8f882a-821d-4d2b-be8c-e62f4912f55b`. The original clinic retains seven bookings and identical booking/config projection hashes. No voice service or model image was changed.

Fresh regression: test_mid backend 278 PASS (91.677 s), frontend 19 PASS plus lint/typecheck/build; website 58 Vitest + 6 Node PASS, build/typecheck, Prettier and public configuration canaries PASS. Source boundary checks report zero failures. Remaining browser/security/accessibility/performance and public staging gates are documented in WEBSITE_WIDGET_ACCEPTANCE.md.

## Performance, actual measurements

| Measure | Baseline | Integrated |
|---|---:|---:|
| Entry JS raw bytes | 130413 | 137287 |
| Same entry Python gzip bytes | 48783 | 51546 |
| Emitted website assets raw bytes | 255302 | 264940 |

The entry grows by 6874 raw bytes / 2763 gzip bytes. Shared loader: 5666 bytes / 2111 gzip bytes, below 4096 gzip bytes. Iframe assets load after the visitor gesture; no speech model or large new SDK loads on the host.

| GET, 20 sequential samples | p50 ms | p95 ms |
|---|---:|---:|
| homepage | 12.71 | 19.08 |
| assistant_route | 32.28 | 40.93 |
| loader | 12.0 | 13.89 |

20 sequential Windows loopback urllib samples per GET, no rendering/throttling/mobile engine; before/after emitted bundle bytes only. No baseline HTTP, mobile, slow-network or LCP/INP/CLS is inferred. Six confirmed-booking turns measured 294.5–362.51 ms, with a mock LLM/calendar. Existing media artifact checks pass.
