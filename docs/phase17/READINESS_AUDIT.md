# Phase 17 prerequisite audit

Checkpoint: 11 October 2026, Europe/Sofia. Decision: **PILOT_BLOCKED**.

Both repositories were clean before Phase 17. Separate `codex/phase17-production-pilot` branches preserve unmerged Phase 15–16 work. Assistant base: d6da61f; website base: 1d40ddd. Main baselines remain 4ddf9ee and 40894dc respectively. No merge, push, production rollout or new spending is authorized by this document.

## Capability classification

| Capability | Classification | Evidence and limits |
|---|---|---|
| Two agents, persistent conversations, permissions, tenant isolation | MOCK_ONLY | Phase 16 offline suite: 328 backend tests; source review of orchestration/store/widget. Not a live model evaluation. |
| Public synthetic HTTPS FAQ and owner Google sign-in | VERIFIED_STAGING | Phase 16 protocol receipts and owner login capture, 11 October; FAQ-only tenant, not booking acceptance. Fresh remote inventory pending scoped authorization. |
| BG Google booking/reschedule/cancel | VERIFIED_LIVE | Phase 14/15 approved provider readbacks, persisted state and replay receipts; BG mail receipt owner-confirmed. Local authorized tenant only. |
| EN Google create/cancel | VERIFIED_LIVE | Phase 15 approved provider readbacks and duplicate checks. EN reschedule and inbox receipt unverified. |
| Reminder scheduling and retry boundaries | MOCK_ONLY | Existing concierge schedule/jobs tests; cancellation receipts. No accepted live reminder delivery. |
| Google-connected public staging booking | BLOCKED | Synthetic staging has no Calendar/Gmail refresh tokens or enabled booking capability. No local customer database migration allowed. |
| Mobile/keyboard | IMPLEMENTED_UNVERIFIED | Local synthetic 320px menu/focus/overflow evidence; public browser, physical device and screen-reader acceptance pending. |
| Qwen/STT/TTS/SIP | BLOCKED | Existing local CPU stack and prior synthetic calls; human-heard bilingual and negative-consent acceptance incomplete. No inference on e2-micro staging. |
| Usage, quotas, quality, privacy funnel | MOCK_ONLY | Phase 16 deterministic tests; immutable ledger reused, quality review does not auto-promote. Provider cost reconciliation and full funnel denominators absent. |
| Backup/restore | MOCK_ONLY | Isolated encrypted SQLite/WAL integrity and tamper tests, not deployed DR rehearsal. |
| Production payments, WhatsApp/SMS, external customer pilot | BLOCKED | No verified provider/customer activation receipts. |

## Actual architecture and deployment inventory

Source: Vue 3/Vite frontend, FastAPI modular monolith, schema-5 SQLite. `semantic_os/deploy/phase15-staging/compose.yml` runs one backend process with persistent data, static frontend/widget and Caddy. No distributed persistence/queue claim; do not enable replicas.

Recorded staging: isolated `testmid-phase15-staging`, us-central1-a, e2-micro, 10GiB persistent disk, IP 34.16.52.243. Origins: assistant-staging.ontelyx.tech (public API/widget), assistant-demo.ontelyx.tech (synthetic site), assistant-admin-staging.ontelyx.tech (owner admin). Fixed stop: 14 October 2026, 20:57:21 Europe/Sofia. Latest deployment evidence is Phase 16, not a fresh Phase 17 health assertion.

Staging tenant `phase15-public-staging`: approved public FAQ only, mock LLM/billing, booking/email/voice unavailable. Local authorized concierge tenant remains separate; Calendar primary and Gmail connections are recorded there, live operations restored off. No credentials, conversations or original encryption key were copied to staging.

Secret references: staging reads G_CLIENT_ID2 and G_CLIENT_SECRET only. ID2 is an alias of the existing client ID, not an independent OAuth client. Owner login requests openid/email only. Existing Calendar/Gmail credentials and unrelated services remain untouched.

CI source inspected: `.github/workflows/ci.yml` includes backend/frontend tests, audits, migration validation and secret/source checks. Website has local test/config/typecheck/build scripts but no `.github` workflow. No fresh remote CI result was retrieved; local results are not proof of hosted CI success.

## Newly identified P0

`semantic_os/backend/assistant/widget.py` clear/retention originally erased messages/provider receipts but retained arguments/handoffs/results in agent/tool traces. Phase 17 adds shared redaction with owned-conversation and cross-tenant regression coverage. Durable appointments are deliberately separate; this is not upstream or full tenant erasure.

## Evidence commands

Executed: `git status --short`, `git branch --show-current`, `git log`, bounded reads of Phase 16 release/security/operations reports, CI manifests, `widget.py`, `privacy.py`, `concierge.py`, website package scripts. Neither repository had uncommitted changes at the baseline.

Historical tests: 328 backend,31 frontend,78 website; final Phase 16 logs under ignored `artifacts/phase16`. New Phase 17 results are recorded separately; none of these certify pilot readiness.
