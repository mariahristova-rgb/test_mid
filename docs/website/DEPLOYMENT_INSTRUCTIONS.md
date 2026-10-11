# Review and staging deployment instructions

No public deployment or production merge/push is performed. Confirm Netlify Git-trigger behavior and review both feature-branch diffs before any remote push that could launch a deploy preview.

## Local review

Actual website checkout: `artifacts/phase13b/ontelyx`, branch `codex/phase13b-assistant-integration`. test_mid branch: `codex/phase13b-website-integration`. The website is an independent Vue/Vite repo, not a copy of the AI backend. Its Netlify pipeline remains `npm run build` → `dist`.

Open http://127.0.0.1:5173/ai-assistant/ or the homepage floating entry. App dashboard is http://127.0.0.1:3017; local login `demo / 0000`; choose **Ontelyx Website Demo**. Widget origin is 3020. Use only fictional data. Browser voice is unavailable. The local nginx review configuration uses relative redirects so host port 5173 is preserved.

Rebuild website with `npm ci`, `npm run build`, `npm test`, `npm run test:config`, `npm run format:check`. Its ignored `.env.local` contains only generated public ID/origin. Do not copy private backend secrets into that file.

The local root compose stack combines `compose.cpu-voice.yml`, `compose.cpu-neural.yml`, `compose.cpu-widget.yml` and `compose.ontelyx-review.yml`, using the existing ignored `artifacts/local-demo/compose.env`. `ONTELYX_WEBSITE_DIST` points to the actual website dist. The extra nginx container is limited to 96 MiB/0.5 CPU and bound to loopback; no model duplicate or speech/SIP restart is required. Inspect active calls before backend updates, and wait for backend healthy readiness before using the frontend: otherwise transient 502 is expected.

`scripts/phase13b_ontelyx_demo.py prepare` provisions the dedicated synthetic tenant using existing authenticated APIs and creates a local ownership file/public config. Build the website before `verify`, which performs the authorized fictional booking journey once. Do not reprovision or point these scripts at real tenants. Dynamic verification files, credentials, node_modules, dist and local evidence are ignored by website Git.

## Staging checklist

1. Owner supplies the approved HTTPS widget/API and website staging origins. They must be distinct from each other and staff/model origins.
2. Set production/staging identity, database, secret references, retention, quota/abuse controls and TLS in test_mid. The existing public widget demo promotion allows mock providers only; do not label it a real calendar/model deployment.
3. Create a dedicated staging demo tenant, apply the approved public FAQs/instructions and test both languages with its exact schedule/config. Explicitly activate and configure its widget. Never reuse the clinic tenant or confidential knowledge.
4. Generate a fresh domain nonce. Publish only that bounded ownership file on the authorized website; verify it through test_mid. Local loopback fetch mappings are demo-only and ignored in strict deployment. GitHub repo access is not website-origin proof.
5. Set the website's **build-scope** `VITE_ASSISTANT_WIDGET_ORIGIN=https://…` and generated `VITE_ASSISTANT_PUBLIC_ID=wdg_…`. Leave both empty to disable. Hosted builds reject HTTP loopback, partial pairs, credentials and non-origin URLs. Preserve Auth0/Cookiebot config and paused public auth.
6. Publish a tested widget version; verify website loader/iframe/bootstrap/chat/language/booking/retention/clear and dashboard results on desktop/mobile with keyboard/screen reader, slow network and offline retry. Record actual Web Vitals; size/HTTP measurements are insufficient.
7. Review CSP script/style/frame/connect sources and iframe frame-ancestors against real staging domains and nested CMS frames. Retain microphone denial until approved voice acceptance. Existing Netlify `upgrade-insecure-requests` means local HTTP URLs cannot be used for a hosted preview.
8. Test unapproved origins, forged-origin limitations, replay/expiry, tenant isolation and unpublish/revoke. Staging controls require edge abuse monitoring in addition to server quotas.
9. Review secrets/canary scan and independent builds in both repos. Owner approves public deployment/production merge separately. Do not merge directly to production branches or create paid services automatically.

Rollback: unpublish the demo widget immediately; restore compatible previous widget version; disable website integration by removing both public build settings and rebuilding the reviewed feature release. Revoke permanently retires an integration; make a new public ID rather than reactivating it. This does not delete separate demo bookings or restore unrelated tenant calendar policy.
