# Implementation status

## Phase 10 Stage A — 2026-10-10

Baseline source audit, official public competitive evidence, persona journeys, original bilingual wireframes and focused P0 proposal are documented in docs/ux. Stage A approval was requested before redesign, as required by the Phase 10 instructions. No Phase 10 product functionality is implemented yet; no deployment or voice/provider change occurred. Phase 9 remains DEMO_BLOCKED. Latest Phase 10 regression results and outstanding acceptance are in docs/ux/PHASE10_TEST_RESULTS.md. Historical entries below describe their own verification dates and are not current release approval.

## Phase 7 / 7B / 7D local increment

Latest verification: 204 backend tests passed in 67.426 seconds; frontend typecheck/lint/build and 9 tests passed; 152-file source boundary and staged redacted secret scans passed. A correct-details English Windows SIP workflow created appointment 17b331e6-fda5-4735-8f88-1fd45d0e7b31 for Jane Smith, 12 October 2026 at 15:00 Europe/Sofia. Bulgarian reached the correct proposal but confirmation still failed. No three-consecutive bilingual success or production readiness is claimed. Actual visual dashboard inspection was rejected by browser security policy and remains pending. The 197-test count in the earlier paragraph below is superseded.

The shared Qwen provider is routed through the existing agents with guarded structured output/tools, usage receipts, call-ID handoffs and cancellation. Private ARI/RTP, local speech workers, the dedicated SmileCare seed/reset, bilingual persisted call activity and scoped Windows demo scripts are implemented. The original GCS Qwen weights were verified and separately converted to Q4_K_M; actual CPU loading, model probes, Windows SIP registration/call establishment and non-silent RTP greeting are verified. Actual speech-quality and latency failures are recorded. **Three consecutive successful booking journeys are not achieved; local demo/production readiness is not claimed.** Latest complete backend suite: 197 passing tests. See LOCAL_DEMO_READINESS and VOICE_LATENCY_RESULTS for limits and actual evidence. Earlier Phase 6C blocker text below is historical and superseded by this increment.

## Phase 6C increment — prerequisites blocked

Read-only pinned GCS artifact/cache contracts, a standalone bounded Qwen compatible-endpoint adapter and nine offline contract tests were added. Neither adapter is enabled in the product. No Qwen location/endpoint or accepted local Bulgarian voice is supplied; actual routing, speech, Asterisk/RTP, SmileCare seed and real-call acceptance remain incomplete. See `docs/voice/SELF_HOSTED_VOICE_AUDIT.md` and `docs/demo/VOICE_TEST_RESULTS.md`. This increment does not establish self-hosted demo or production readiness.

The functional SaaS hardening foundation is implemented in `test_mid`, preserving the Phase 1–4 application. **Real payment processing and all live provider accounts remain unverified. Production readiness is not claimed.**

## Baseline and implemented scope

Before changes, 131 backend tests, 7 frontend tests, frontend typecheck/lint/build and the 74-file source boundary check passed. Phase 1 cleansing, Phase 2 agents/booking, Phase 3 synthetic voice and Phase 4 messaging persistence were reviewed. No proprietary semantic runtime dependency remains in the application.

| Area | Implemented | Verification / remaining gate |
|---|---|---|
| Onboarding | Server-generated tenant, initial admin/assistant/two agents, verified email binding, timezone/locale, trial/checkout and state gates | Both languages and pending/verified access tested; real IdP verified-email claims must be configured |
| Billing | Provider-independent plans/subscriptions/items/customers/invoices/events, monthly/annual terms, version snapshots, upgrades/downgrades/cancel/renew/grace/suspend | Mock signature/idempotency/underpayment/renewal tests; no live checkout or charge |
| Entitlements | Active resources, re-enable checks, AI/agent/tool/channel counters, voice budgets, storage and retention, hard/soft/warnings | Backend and concurrent-send reservation tests; real vendor limits require evaluation |
| Usage | Append-only ledger/triggers, semantic idempotency, UTC period, integer amounts, rate snapshots, closed-period usage invoice and reconciliation | Exact monetary tests; actual LLM tokens/vendor billing remain unreported/unreconciled |
| Credentials | Encrypted keyring, versioning, explicit rotation/revocation, ownership checks, masked metadata and access audits | Tenant, keyring and revocation tests; managed deployment/offsite key custody required |
| Privacy | Tenant/contact export, explicit erasure requests/execution, media/identity redaction, access revocation | Tested on synthetic records; financial/audit/provider/backup retention is separate and not GDPR certification |
| Operations/support | Content-free correlation/timing/error metrics, worker/backups/failure visibility, platform metadata and expiring audited support grants | Scope/denial/revocation tests; external metrics/alerts and support process remain operating integrations |
| Reliability | Existing transactional inbox/outbox, bounded safe retries, unknown-send reservations, lifecycle draining, health checks | Existing workflows preserved; unknown external results require verified reconciliation |
| Database/recovery | Forward migration 5, ledger index/triggers, consistent authenticated encrypted snapshots and fresh-target restore | Clean/replayed migrations, in-memory and disk WAL restore, actual staging recovery verified |
| UI | Bilingual onboarding/billing/usage/operations/admin screens, exact BigInt currency display, warnings/held allowance, reuse of Vue components | Browser flows and localization/type/lint/build checks; lists remain unpaginated |
| Deployment | Pinned Python constraints, audited frontend lock, origin-specific CSP, non-root containers, TLS staging/production recipes, CI gates/artifacts | Local staging works; no hosted production deployment or real identity/provider account is claimed |

## Observed checks

- Backend suite: **168 tests** (original 131 plus 37 SaaS cases), covering prior channels and new lifecycle, quotas, concurrency, billing/security/privacy/backup cases. Synthetic credentials/providers only. Tests include exact minute/second configuration, monthly limits replacing the legacy lifetime counter, and early-callback/dispatch metering without duplicate usage.
- Frontend suite: **9 tests**, including all literal translation keys and exact large minor-unit currency formatting. Vue typecheck, zero-warning lint and Vite build pass; source/bundle environment-secret scans pass.
- Browser: preserved bilingual booking, human takeover, quarantine, channel configuration and synthetic voice controls pass. New Bulgarian/English registration, verification, trial, mock checkout, exact currency, usage and operations pass. HTTPS staging browser verifies signed identity and Bulgarian billing.
- Dependency security: Python pinned application audit reports no known vulnerabilities; npm audit reports **zero** after fixing three high/two moderate findings. No peer-validation bypass or forced incompatible install was used; a clean graph was resolved and installed with scripts disabled.
- Source/import/syntax boundary check: **102 files, zero failures**. Gitleaks scans app images and **154 staged Git-visible source/config/docs files**, with no leaks found. Ignored local staging material is never copied into the frontend build or source scan.
- Migration artifact: versions 1–5, integrity/foreign keys and preservation/replay pass. Existing versions 1–4 are unchanged.
- Local HTTPS staging: certificate validation, readiness, headers, tenant denial, Bulgarian/English shared conversations, mock billing, worker/automated backup and fresh-target restore pass. The final recorded synthetic backup + restore elapsed approximately **2.66 seconds**; configured RPO/RTO targets are 86400/3600 seconds.
- Performance fixture: Windows/Python 3.12.10, 16 logical CPUs, temporary SQLite/WAL and in-process ASGI with tracemalloc. Thirty conversation+agent+tool operations per concurrency level: about **10.15/13.86/13.39 operations/s** at concurrency 1/4/8, p95 **115.95/390.74/688.76 ms**, zero errors. Ten inbound + ten outbound jobs took about **0.56 s** with no dead letters. Eight synthetic call-admission attempts accepted four and rejected four; no real phone/audio load was generated. These are local fixture results, not production capacity or SLA claims.

Evidence: [SaaS demonstration](SAAS_DEMO.json), [staging/recovery](STAGING_VERIFICATION.json), [measured performance](PERFORMANCE_RESULTS.json). All A–E requirements are covered by offline/backend/browser demonstrations; the actual staging exercise uses mock providers and a synthetic signed issuer.

Staging exposed and corrected missing fixture customer provisioning, unprivileged gateway runtime paths and WAL deserialize recovery handling. An on-disk regression test now covers the recovery issue. Windows sandbox temporary-file/socket restrictions required permitted offline retries. Starlette's future httpx2 notice, pip-audit's hash recommendation and the development ESLint 9 support notice are recorded maintenance items, not evidence of production certification.

## Production blockers

Real hosted payments, platform-owned payment credentials, taxes/legal invoices/refunds/disputes, verified provider usage and actual billing collection are absent. IdP/email-verification configuration, real LLM/calendar/speech/carrier/Meta/SMTP accounts, public TLS/DNS/renewal, external logs/alerts, offsite backups/key custody, retention/provider erasure policy, legal/security review and production-scale capacity/recovery must be verified before commercial launch.

The supported topology remains one process/SQLite writer, local limiter/aggregates, bounded voice pool and unpaginated histories. LLM token measurements are not invented. Some speech counters are conservative attempted-input units and remain nonbillable pending vendor reconciliation. Prepared subscription notices are mocked, not delivered mail. Quarantined files lack a production malware-release pipeline.

CI configuration runs audits, tests, type/lint/build, migrations and artifact generation. Its checks were reproduced locally; no remote GitHub workflow execution or public deployment is claimed. No original repository was modified and no real customer data or payment was deleted/charged. Temporary fixture services are shut down after verification; dedicated synthetic staging volumes are retained.

See [readiness audit](PRODUCTION_READINESS_AUDIT.md), [SaaS](SAAS_ARCHITECTURE.md), [billing](BILLING_ARCHITECTURE.md), [usage](USAGE_METERING.md), [security](SECURITY.md), [deployment](DEPLOYMENT.md), [recovery](BACKUP_RECOVERY.md) and [bilingual support](BILINGUAL_SUPPORT.md).

## Phase 8 measured outcome — 9 October 2026

Phase 8 adds bounded audio pre-roll, a demonstrated demo-only VAD endpoint correction, clear Bulgarian reservation consent, guarded literal cancellation and safer name-prefix handling. Existing tenant-scoped agents, tool permissions, approval/idempotency, conversations and mock calendar remain. Original Qwen3-4B BF16 artifacts are preserved; the existing derived Q4_K_M model is unchanged. No paid managed provider, larger LLM or Ontelyx proprietary semantic runtime was introduced.

Verification: 208 backend tests passed (57.674 s); frontend typecheck/lint/nine tests/build passed; source boundary check 158 files/zero failures; redacted offline secret scan 249 staged files/zero findings. Required Phase 8 documentation and actual audio/call evidence are present. Commercial deployment and live-demo readiness are not claimed.

**PARTIAL / BLOCKED.** Three real SIP attempts finished, but the booking release gate did not pass. Registration, call establishment and response packets are separate from caller-heard confirmation. Known locale was selected through the existing authenticated call-language control; no STT transcript was injected. Synthetic WAV callers were used, not representative human callers. Raw live transcripts remain disabled by the existing privacy settings.

| Locale | Attempt | Call ID | Last booking state | New confirmed bookings | Request/name/confirm observation ms |
|---|---|---|---|---|---|
| bg-BG | 20261009T100552Z-92117b | 7231118e-9424-4daa-a87a-3e3a46279cc4 | awaiting_confirmation | 0 | 33484/44953/68437 |
| en-US | 20261009T100926Z-58c039 | 1b8ef3fe-c435-46ec-94a3-a6b57cd11df5 | awaiting_confirmation | 0 | 26110/30734/73907 |
| bg-BG | 20261009T101251Z-931cd0 | 099194ab-20ff-44b1-90fd-a5afa9b292d6 | awaiting_confirmation | 0 | 29609/41047/68281 |

Each attempt retains its input hashes, received WAV, redacted signaling, resource samples, conversation, agent handoffs and tool results under artifacts/phase8/sip-tests/<attempt>/. The summary is artifacts/phase8/three-call-results.json. State observation timings include input playback, buffering, inference and polling; they are not synchronized first-audible latency. No new correct booking or three-call success is inferred. The prior correct English booking remains historical evidence, not a Phase 8 pass.

Required remaining gates: reliable telephone-band time/consent recognition, caller-heard intelligibility, real in-call language switching/unavailable/interruption/failure scenarios, visual dashboard verification and three consecutive complete correct bookings. Existing unit tests do not establish those live gates. Browser security policy rejected local dashboard inspection; no indirect or alternate-browser bypass was attempted.

## Phase 8B measured update — 9 October 2026

Implemented the smallest confirmation fix: exact clear consent in an existing unexpired proposal is decided deterministically, without a second probabilistic intent veto. Executor/tool/approval authorization, fingerprint/expiry, availability and idempotency checks remain. Rejection, explicit requested slot replacement, voice expiry and disconnect invalidate an outstanding proposal; playback, segmentation, handoff and short silence retain it. Ambiguous text explicitly asks for clarification. Web Chat HTTP expiry behavior is preserved.

Content-free bounded tenant traces correlate all supported stages. Local STT is final-only; partial_supported=false is explicit. Nine new regression tests cover durable single execution/replay, rejection, ambiguous/question transcripts, expiry, requested changes, locale retention, trace privacy/tenant bounds, disconnect cancellation and rollback-safe persistence tracing. The initial full suite passed 216 tests in 47.318 seconds; the final report below reflects any later trace correction. Focused finalized voice/confirmation regressions passed 41 tests in 10.400 seconds. An earlier 215-test full run also passed; the initial targeted web expiry regression was corrected before deployment. Only the backend image was rebuilt; no inference models or working infrastructure were rebuilt.

Acoustic recovery remains partial. Twenty-seven actual PCMU trials found a question waveform transcribed as literal consent. Deterministic text safety does not fix ASR loss of interrogative meaning. No broad keyword, fuzzy spelling, negative-word dropping or expected-transcript injection was introduced. General speech consent safety and human/live verification are not claimed.

**PARTIAL / BLOCKED.** Deterministic confirmation is recovered; complete live acceptance is not inferred. The owner declared availability for live acceptance before new SIP attempts. Caller fixtures combine existing BG38 speech and authorized Ivan evaluation speech; the assistant's response provider remains BG38. Known locale is selected through the existing authenticated control, without transcript injection.

| Locale | Attempt | Call ID | Business workflow | Booking IDs | Human-heard verification |
|---|---|---|---|---|---|
| bg-BG | 20261009T105422Z-29fa08 | 38d1e640-f178-4b59-a901-021bbd8103e8 | True | e1918d21-a585-4b07-85dc-2947b037c450 | pending |
| en-US | 20261009T105839Z-e5d106 | 8c3cb1f5-ab9e-4853-890a-6180ed1a0e11 | True | 4c04be6e-27f1-4925-9737-3f6c7ff79a91 | pending |
| bg-BG | 20261009T110159Z-7f0d1a | 33c8e022-7c76-4ad2-a4c6-765caebd2c62 | True | f170806c-a94b-4c58-9379-cae95c27e9e2 | pending |

Three consecutive complete calls, human-audible correct confirmation, visual dashboard evidence and the acoustic question false-positive control remain open gates. Received RTP/nonzero WAV/persisted row alone cannot satisfy human acceptance. New receipts are artifacts/phase8b/sip-tests/<attempt>/; prior unsuccessful attempts remain in Phase 8 evidence. Sequence continuation is permitted only after the preceding business journey passes; no failure is silently omitted. Browser policy previously blocked local inspection and is not bypassed; the owner can verify the dashboard directly.

All three consecutive selected-affirmative SIP business journeys passed. Each created one distinct correct appointment, and response audio reached the caller transport. All three survived the targeted backend restart; no active API calls or Asterisk channels remain. Caller-side final-45-second excerpts were provided for human listening. This is business/transport evidence, not full human acceptance.

The owner initially reported ERR_CONNECTION_REFUSED when checking the dashboard. The intended URL is http://127.0.0.1:3011/dashboard; the existing listener was verified on 127.0.0.1:3011 and returned HTTP 200. Visual booking verification remains pending the owner’s follow-up; HTTP availability is not visual proof.

Latest complete backend suite: 217 tests passed in 57.213 seconds.

Preserved frontend verification: typecheck, zero-warning lint, nine tests and build all passed, including source/bundle environment-secret scans. Source boundary check and final staged secret scan results are recorded separately. Final backend is healthy with rollback-safe trace; the three bookings survived its restart. The current Qwen/STT/BG38 model services remain unchanged.

## Phase 9 — blocked release preparation

**DEMO_BLOCKED — preparation only.** Phase 8B has not passed the mandatory human/speech acceptance gate. No release candidate is certified and no new Phase 9 live rehearsal, reset, public release or real notification was performed.

243 backend tests passed in 55.353 seconds. Fresh frontend nine tests, lint, typecheck and build pass. Read-only health/inventory, fixed dated plan, bilingual presentation/recovery/checklist documents and isolated reset safeguards are prepared. The reset preserves seeded fixtures, rejects active/foreign/unmarked tenants and requires explicit CLI/PowerShell confirmation; live data was not reset. No RC, commit/tag, public release, deployment, new live rehearsal or real send was performed. See docs/demo/PHASE9_READINESS.md for exact blockers and evidence.
