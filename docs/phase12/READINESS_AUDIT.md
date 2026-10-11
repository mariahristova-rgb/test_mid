# Phase 12 prerequisite audit

10 October 2026. Repository-only work; no cloud resources or public deployment. Phase 11 changes are present but uncommitted on top of 213e0ce; preserve that work. This audit does not turn historical tests into fresh Phase 12 verification.

| Prerequisite | Classification | Evidence / implication |
|---|---|---|
| Local demo sign-in | VERIFIED (prior scoped receipt) | Phase 11 local checks confirm demo login; production identity remains separately unverified |
| Tenant registration/account verification | IMPLEMENTED_UNVERIFIED / MOCK | Existing SaaS registration, membership, verification and plans; local email verification uses a mock |
| Resumable assistant draft | IMPLEMENTED_UNVERIFIED | Phase 11 SetupView / ux.py; API regressions pass, full observed journey remains pending |
| Two agents / persisted chat and appointments | VERIFIED within recorded tests | Existing Orchestrator, booking workflow and SQLite tenant ownership; rerun Phase 12 regression |
| Approved bilingual FAQ | IMPLEMENTED_UNVERIFIED | AssistantConfig FAQ entries and exact-match responses; no proprietary knowledge runtime |
| Scheduling | MOCK | Persisted appointments with mock calendar policy; no live clinic calendar integration |
| BG/EN sandbox | VERIFIED within Phase 11 API scope | Disposable stores, bounded mock receipts; not proof of real-model or audio quality |
| Draft/active versioning | IMPLEMENTED_UNVERIFIED / MISSING rollback | Phase 11 promotion history exists; immutable visitor snapshots and widget rollback missing |
| Universal loader/iframe | MISSING | No widget sources or routes found |
| Public visitor authentication/origin checks | MISSING | Staff bearer credentials must not be embedded or reused for visitors |
| Domain ownership/install proof | MISSING | Existing messaging origin fields are not widget ownership or installation evidence |
| Public widget retention/quotas/revocation | MISSING | Existing tenant controls are reusable, but visitor-specific controls need implementation |
| Cloud deployment | IMPLEMENTED_UNVERIFIED foundation | Existing staging/production Compose templates; single-process SQLite cannot simply be replicated |
| Voice/SIP live acceptance | BLOCKED | Phase 9 consent, Bulgarian dated speech and human acceptance remain blocked |
| Desktop/mobile/accessibility/browser performance | BLOCKED / IMPLEMENTED_UNVERIFIED | Previous browser security denied inspection; no browser E2E, screenshots or Web Vitals may be invented |

Phase 11 is explicitly not fully accepted in PHASE11_ACCEPTANCE.md. This contradicts the prompt's reported-complete premise; its implemented code is retained and reused. Phase 12 does not certify telephone or production readiness.

## First fictional customer journey

Local demonstration sign-in → existing registration creates a new isolated tenant → complete explicitly mock email verification if needed → configure Receptionist/Support/Sales instructions, BG/EN FAQs and demo scheduling → save/resume → run scoped sandbox tests → register sample-site origin and prove control with a nonce file → generate one-script snippet → publish immutable widget version → install on a different local origin → chat and explicitly confirm a persisted demo booking → inspect the tenant dashboard → unpublish/revoke.

Real public registration depends on a verified production identity configuration. Shared local demo credentials are not a customer identity service. Domain proof, snippet generation, HTTP reachability, browser installation and successful conversation are separate facts.

## Scoped implementation plan

1. Extend existing draft/configuration surfaces and SaaS onboarding; no replacement auth framework or component library.
2. Add tenant-owned widget integrations, immutable snapshots and version pointers using the existing persistence conventions. Promotion uses matching test evidence and explicit confirmation; rollback cannot silently alter unrelated business policy.
3. Introduce a versioned, small host loader and dedicated-origin iframe. No model/SIP keys or large SDKs enter host pages. Text-only UI; microphone/voice absent while unverified.
4. Bootstrap a one-use admission ticket from an allowed origin, redeem it inside the iframe for a short-lived conversation-only credential, hash credentials at rest and enforce revocation, quotas and tool restrictions server-side. Origin is an admission policy, not identity.
5. Verify site authorization using a bounded nonce-file challenge, with SSRF protections. Local-loopback verification is limited to the explicitly configured example origin in development.
6. Run new-tenant BG/EN booking, replay, isolation, expiry/revocation, origin/CORS/CSP and publishing/rollback tests. Serve a real separate-origin sample. Browser/mobile/a11y gates remain unverified if the security block persists.
7. Record actual loader/API measurements, installation instructions, portable cloud topology and unresolved gates. No paid resources, real sends, public exposure or voice/model changes.

## Post-implementation classification

VERIFIED by automated/API evidence: new isolated tenant, eight bilingual sandbox cases, actual nonce-file ownership check, two persisted confirmed demo bookings, duplicate prevention, origin/RBAC/session/lifecycle/quota boundaries and unchanged original clinic state. MOCK: LLM/calendar, verification email and billing. IMPLEMENTED_UNVERIFIED: linked browser onboarding, lazy iframe, brand/privacy/language controls, human-reply polling, CMS installation guidance and cloud template. BLOCKED: desktop/mobile browser E2E/a11y, visual dashboard acceptance and browser Web Vitals. MISSING for production: distributed quotas/database/queue, edge abuse controls, complete retained-business-data deletion verification and real provider promotion. WIDGET_DEMO_READY is not claimed; see E2E_ACCEPTANCE.md for final evidence.
