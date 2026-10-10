# Phase 9 readiness decision

**DEMO_BLOCKED — preparation only.** Phase 8B has not passed the mandatory human/speech acceptance gate. No release candidate is certified and no new Phase 9 live rehearsal, reset, public release or real notification was performed.

Audit: 2026-10-09T11:32:44.587587+00:00. All seven prerequisite reports were inspected; latest actual Phase 8B per-call receipts and acoustic controls were checked rather than treating the prior summary as approval.

## Exact blockers

- Human-heard Bulgarian and English confirmations remain unverified
- Actual dashboard call/conversation/agent/tool/booking visibility remains unverified
- Telephone-band ambiguity/negative/question recognition safety has not passed
- Git has no commit; the working tree cannot be identified as a committed release candidate

Three selected-affirmative synthetic SIP business workflows passed in Phase 8B with distinct appointments and restart persistence. They are not three human-accepted calls. The owner reported an initial dashboard connection refusal; the intended port 3011 returned HTTP 200, but actual visual rows remain unverified. The Ivan telephone-band question control became affirmative in all three decode variants. These are mandatory failures; DEMO_READY_WITH_LIMITATIONS cannot waive them.

## Isolated preparation completed

Read-only readiness command, version inventory, fixed dated presentation plan, safe reset confirmation/seed preservation, disposable reset/idempotency/isolation tests, bilingual presenter scripts, customer-journey/recovery/checklist documents. Existing bounded two-second UI polling is retained; no dashboard redesign or new live event simulation was added. Bilingual templates are present; current tenant Email/SMS/WhatsApp connections are NOT_CONFIGURED. Four existing offline mock messaging scenarios were reproduced independently, not delivered or inserted into the live dashboard.

Fresh verification: 222 backend tests passed in 48.999 seconds. Frontend nine tests, lint, typecheck and build were rerun and passed. Source/secret checks are recorded in artifacts/phase9/final-checks.json when complete. No proprietary semantic runtime or paid voice provider was introduced. Backend reset safeguards are source changes for offline maintenance; they were not deployed to or exercised against the running database.

## Reproducibility inventory, not a release

Git has an unborn codex/phase1-repository-audit branch, no commit and Git-visible source/config/docs untracked. This is documented uncommitted work, not a clean committed RC. No new branch/tag/version, remote push or public release was created. Frontend's existing application version is 0.1.0; no independent backend release version is declared. RC identifier and Git commit remain null.

Qwen: hf-1cfa9a7208912126459214e8b04321603b3df60c, Q4_K_M, SHA-256 9a91506f18e56bfa9389a939db1b36029daf8c49327b0eb0bc9e19d627b00e79. Original BF16 assets are untouched. STT: hf-536b0662742c02347bc0e980a01041f333bce120. TTS: BG38 3f6ca06b3ca78352eb00d8e96349c0bedaa3d2f1 and MioCodec 3a737f0de2c6324cb2fe40c1fbd1056c7add423d; Windows Ivan remains evaluation-only. Migration version: 5.

| Service | Running image ID | Runtime state |
|---|---|---|
| asterisk | sha256:a8f0e18a71b691507ce7c4973991451e9f6a5321ad5845884f9c3856598fade3 | RUNNING |
| qwen | sha256:33868c035b21dc63f7c60b7438774283fd99215bc319114eb03de5df4ce7cd6b | HEALTHY |
| stt | sha256:541f16e21879399e543e4462c58b11eec14195c39f9e84b184fe0b724c7b7afd | HEALTHY |
| tts | sha256:556b541f9d544fb0c84aebc90cd3d24bb94639bf204fafc346f7ed97a9df8920 | HEALTHY |
| backend | sha256:b94e443f25b942dc13883583cb6087a428258f663b39b365b4ee29b09b065734 | HEALTHY |
| frontend | sha256:934d62a91a53940d3485178af0bb1e3f4f0d6e49b02ff459833e14f18e65f594 | RUNNING |

Pinned image references/model revisions and dependency/configuration hashes are captured in artifacts/phase9/version-inventory.json. Runtime image IDs are existing local images, not newly published immutable release artifacts. Python constraints, frontend lockfile and both Compose files are retained. This audit does not rehash all model weights; existing verified startup caches are preserved.

## Required next gate

Resolve the acoustic consent control failure, obtain genuine BG/EN listening and visual dashboard evidence, then repeat three consecutive complete SIP journeys. Only then freeze a reviewed source commit/configuration, build a dedicated RC, rehearse fixed dates/reset/restart and decide release readiness. Public-network calling, real clinic calendars, real notifications/payments, production identity/security/recovery/capacity remain separate unverified integrations.

## Continuation — 10 October 2026

The existing demo containers were restored with --no-recreate --no-build --pull never after Docker became available. All prior three Phase 8B bookings remain confirmed and no call session is active. No reset, new SIP acceptance call, image replacement, model download or release certification occurred. The configured dashboard is http://127.0.0.1:3011/dashboard; port 3017 is not this scoped stack.

Reset now fails closed if Docker status cannot be verified, before Python/SQLite maintenance; a Windows subprocess regression executes the actual wrapper with a failed diagnostic. Readiness now requires all negative/rejection/ambiguous/question controls and registered SIP establishment/clean termination evidence. Missing evidence cannot become a pass.

Fresh full backend run: 224 tests passed in 111.824 seconds. The focused preparation suite passed 8 tests in 10.513 seconds, including the additional wrapper test added after the full run. Source check: 168 files, zero failures. Offline redacted secret scan: 283 files, zero findings. Frontend was unchanged; its prior Phase 9 checks are historical, not rerun today.

Current evidence: artifacts/phase9/readiness-20261010.json and continuation-20261010.json. Release remains DEMO_BLOCKED: human-heard/visual acceptance, acoustic question safety and a committed source candidate are still missing.
