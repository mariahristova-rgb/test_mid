# Multi-channel AI Assistant foundation

Independent Vue 3/FastAPI modular monolith with tenant membership, two agents, bilingual UI and conversations, validated business tools, appointments, reminders and five communication contracts. The application directory remains `semantic_os/` for checkout compatibility; no proprietary runtime is loaded.

## Dedicated local voice demo — release blocked

Phase 9 decision: **DEMO_BLOCKED**. Three Phase 8B synthetic SIP business workflows persisted correct bookings, but human-heard confirmation, visual dashboard acceptance and a failed acoustic question-consent control remain open. Healthy containers and mocked integrations do not certify an external demonstration or production launch. See [Phase 9 readiness](docs/demo/PHASE9_READINESS.md) and [release checklist](docs/demo/DEMO_RELEASE_CHECKLIST.md).

The existing Windows/Docker CPU stack uses local Qwen3-4B Q4_K_M, multilingual small STT, BG38/MioCodec TTS and a mock clinic calendar. Dedicated Docker dashboard: **http://127.0.0.1:3011/dashboard**. Port 3000 below is the separate frontend development server.

The local demo also serves **http://127.0.0.1:3017/calls**. Its username/password form uses username `demo` and the owner-configured password in the ignored, protected `artifacts/local-demo/secrets/demo_login_password.txt` file. It selects the existing SmileCare tenant automatically. The credential exchange requires explicit demo enablement and loopback/trusted private proxy access; staging/production demo authentication remains prohibited. Browser access tokens stay in memory. Refresh an already-open tab after updating the frontend image.

Read-only readiness command:

```powershell
powershell.exe -NoProfile -File scripts/demo/readiness.ps1
```

An explicit blocked result is expected; details are written to `artifacts/phase9/readiness.json`. Prepared [customer journey](docs/demo/DEMO_CUSTOMER_JOURNEY.md), [Bulgarian](docs/demo/PRESENTER_SCRIPT_BG.md)/[English](docs/demo/PRESENTER_SCRIPT_EN.md) scripts, [recovery](docs/demo/DEMO_TROUBLESHOOTING.md) and [reset](docs/demo/DEMO_RESET.md) instructions preserve the acceptance blockers. Reset now requires `-Confirm`, a stopped dedicated writer and the marked fictional tenant, and preserves seeded fixtures. It was tested in disposable stores; the live demo was not reset. No RC commit/tag, public release, real message or public-network phone test was performed.

**Default provider status: MOCK.** Chat, configuration, persistence, approvals, synthetic voice and signed multi-channel inbox/outbox workflows work. Phase 5 adds onboarding/verification, subscriptions, backend entitlements, immutable usage, credential lifecycle, privacy/support controls, operations, encrypted recovery and isolated HTTPS staging. All real provider/payment operation remains unverified; no production-readiness claim is made. See [implementation status](docs/architecture/IMPLEMENTATION_STATUS.md), [SaaS architecture](docs/architecture/SAAS_ARCHITECTURE.md) and [readiness audit](docs/architecture/PRODUCTION_READINESS_AUDIT.md).

## Local development

Use Python 3.12 and Node 24. Work only inside this checkout. Existing environment files and runtime workspaces are ignored by the new app; do not copy their contents into new configuration.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c semantic_os/backend/requirements.lock -r semantic_os/backend/requirements.txt -r semantic_os/backend/requirements-messaging.txt
$env:ASSISTANT_DEMO = 'true'
$env:ASSISTANT_DEMO_TOKEN = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
$env:ASSISTANT_ENCRYPTION_KEY = .\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
.\.venv\Scripts\python.exe -m uvicorn semantic_os.backend.api.app:app --host 127.0.0.1 --port 8000 --no-access-log
```

Keep the generated encryption key in your development secret manager if you want to reopen encrypted connections. Changing it makes existing encrypted secrets unreadable. Never use a new random key for an existing database. Demo auth is explicit, restricted to loopback and prohibited in production. With demo disabled and Auth0 absent, protected routes deny access.

Messaging connections are configured in Channels or `/api/messaging/connections`; provider credential inputs are encrypted and never returned. Signed inbound events enqueue work. Run `/api/jobs/run` with explicit confirmation, or enable the bounded single-process worker with `ASSISTANT_MESSAGING_WORKER_ENABLED=true`. Both live messaging flags default false. Email replies default to approval drafts; automated SMS/WhatsApp notifications require consent, and out-of-window WhatsApp requires a provider-verified localized template. Use [adapter contracts](docs/architecture/CHANNEL_ADAPTERS.md) for webhook examples and integration gates.

Reproduce all four Phase 4 scenarios without any real send:

```powershell
.\.venv\Scripts\python.exe scripts/demo_multichannel.py --output docs/architecture/MULTICHANNEL_DEMO.json
```

The artifact verifies Bulgarian WhatsApp booking, English email next-Monday clarification/thread/draft, Bulgarian SMS reminder/segments/callback/idempotency, and human handoff/reply/resume. All fixture data is synthetic. Inbox history refreshes every two seconds; the mock LLM has no token-stream capability. Files remain quarantined until a future scanner/release integration.

Organization setup now creates a separate tenant and its administrator/assistant/agents. Verify the administrator email, select a configured trial or mock checkout, then use Billing/Usage/Operations. Development verification is an explicit local mock; staging/production require verified identity claims. Prices/limits are configured through the separate platform allowlist, never through customer messages. Mock checkout makes no real charge. UI, conversation and voice locales remain independent.

Phase 5 verification and recovery:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s semantic_os/backend/tests -q
.\.venv\Scripts\python.exe scripts/demo_saas.py --output docs/architecture/SAAS_DEMO.json
.\.venv\Scripts\python.exe scripts/check_migrations.py --output artifacts/migration.json
.\.venv\Scripts\python.exe scripts/benchmark_saas.py --output docs/architecture/PERFORMANCE_RESULTS.json
```

See [billing](docs/architecture/BILLING_ARCHITECTURE.md), [usage](docs/architecture/USAGE_METERING.md), [security](docs/architecture/SECURITY.md), [deployment](docs/architecture/DEPLOYMENT.md) and [backup/restore](docs/architecture/BACKUP_RECOVERY.md). Local TLS staging has been exercised with a synthetic signed issuer, dedicated volumes and no live sends. Restoration validates authenticated snapshots and refuses to overwrite existing databases. Production release still requires actual identity/provider/payment/TLS/offsite recovery and legal/operating verification.

In a second terminal:

```powershell
Set-Location semantic_os/frontend
npm ci --ignore-scripts
npm run dev
```

Open `http://127.0.0.1:3000`, enter organization `demo` and the development token generated in the backend terminal. Tokens stay in browser memory. UI language persists separately from conversation/call language. For the demo path, leave `VITE_AUTH0_*` unset; never reuse copied legacy identity settings automatically.

To try the natural-language flow, open Inbox and type `Здравейте, искам да запиша час за утре в 15:00.` or `Hello, I would like to book an appointment for tomorrow at 15:00.`. The assistant detects language, checks the mock calendar, asks for your name, and presents the exact name/date/timezone/duration. Reply `Да, потвърждавам.` / `Yes, confirm.` or click Confirm action. Only confirmation creates the appointment. Relative dates use the initial request timestamp and tenant timezone; repeating confirmation does not book twice. [Core Phase 2 report and demonstration](docs/architecture/AI_ASSISTANT_CORE_PHASE_2.md).

Structured business tools remain available for availability, booking, reschedule/cancel, follow-up, messaging and escalation. In Settings, dispatch due mock reminders explicitly. Background processing requires explicit worker enablement; real sends also require both live gates and tenant credentials. LLM interpretation and calendar are mocked; no external calendar is modified.

For voice, open Calls, start a mock call, then Connect synthetic audio stream. The text area supplies UTF-8 audio fixtures, not microphone sound. Send the same booking request, name and confirmation; both agents and calendar tools are reused. The initial Bulgarian greeting is `Здравейте! Как мога да Ви помогна?`; select English for its equivalent. Recordings/transcripts default off. [Voice architecture](docs/architecture/VOICE_ARCHITECTURE.md) and [telephony setup](docs/architecture/TELEPHONY_INTEGRATION.md) explain signed incoming-call routes, stream tickets and the deliberately disabled live gates.

Reproduce the bilingual synthetic telephone demonstration with `python scripts/demo_voice.py --output docs/architecture/VOICE_DEMO.json`. Actual voice verification requires an explicitly authorized test account/number and real samples; provider documentation/mocks do not establish speech readiness.

## Verified identity and tenants

Configure `AUTH0_DOMAIN` and `AUTH0_AUDIENCE` on the backend, and `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`, `VITE_AUTH0_AUDIENCE` at frontend build time. Register appropriate callback/logout origins with your identity provider. Auth0 verification reuses the existing RS256/JWKS verifier. No identity-provider calls were made during this implementation.

Provision an initial membership using owner-controlled local access, quoting any subject that contains shell characters:

```powershell
python -m semantic_os.backend.assistant.provision --tenant your-organization --subject 'auth0|verified-subject' --role admin
```

This targets the new database only. Subsequent users/roles can be managed by an authenticated tenant administrator. `X-Tenant-ID` is a selector, never an authorization grant: the verified subject must have an enabled membership in that tenant. Admin, operator and viewer roles have different grants. Email addresses never link identities.

## Configuration and deployment

[.env.example](.env.example) contains placeholders only. Load desired settings explicitly into the process; this application deliberately does not auto-load legacy `.env` files. The default database is `.assistant-data/assistant.sqlite3`; migrations create new assistant tables and leave old databases untouched. The MVP supports a single process with a persistent SQLite volume. It is not suitable for multi-instance Cloud Run with ephemeral storage; PostgreSQL infrastructure and a distributed rate limit/queue need a separately validated adapter before that topology.

The revised Dockerfiles keep source scanning, non-root execution and frontend security headers, and remove Spark/JVM and irrelevant SDKs. Compose requires identity/encryption configuration and persistent volumes. Build from `semantic_os`: `docker compose config`, then `docker compose build`. See the status document for observed container validation. Frontend CSP allows HTTPS API/identity origins and local development API; restrict it to exact deployment origins before public deployment. Configure TLS, backups, managed secret rotation and provider-specific authorization outside this local mock foundation.

## Checks

```powershell
python scripts/check_source.py
python -m unittest discover -s semantic_os/backend/tests -v
Set-Location semantic_os/frontend
npm test
npm run typecheck
npm run lint
npm run build
```

Tests use synthetic data and no external providers. CI repeats these checks and runs Gitleaks; Docker also enforces a Gitleaks source scan. Windows API tests need an asyncio loopback socketpair, which may require permission outside a restrictive sandbox. See the status document for actual results, warnings and unverified gates.

## Architecture and privacy

- [Repository audit](docs/architecture/REPOSITORY_AUDIT.md) and [removal report](docs/architecture/SEMANTIC_REMOVAL_REPORT.md)
- [Target architecture](docs/architecture/TARGET_ARCHITECTURE.md) and [data model](docs/architecture/DATA_MODEL.md)
- [Channels](docs/architecture/CHANNEL_ADAPTERS.md), [orchestration](docs/architecture/AGENT_ORCHESTRATION.md), [language and i18n](docs/architecture/LANGUAGE_AND_I18N.md)

Recordings/transcripts default off. Mock audio is UTF-8 fixture data, not playable speech. Retention is an explicit tenant operation that redacts expired message bodies/attachments; full subject erasure and retention of contacts/tool/audit records require an owner policy and further implementation before processing real personal data. This foundation makes no GDPR compliance or legal IP claim. No confidential disclosure documents were incorporated, and original workspaces/data remain untouched.


## Phase15 local product increment

See [audit](docs/product/PHASE15_PRODUCT_AUDIT.md), [implementation plan](docs/product/PHASE15_IMPLEMENTATION_PLAN.md) and [release decision](docs/product/PHASE15_RELEASE_DECISION.md). Current feature-branch work adds grouped navigation and tenant-scoped operator queue/notes to the existing Inbox. Approved BG reschedule/cancel and English create/cancel passed real Google readbacks. Browser/staging/reminder gates remain open; P1 Quality Coach/outcome analytics are not implemented. No Phase15 public release is claimed.
