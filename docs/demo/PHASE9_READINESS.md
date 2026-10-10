# Phase 9 readiness decision

**DEMO_BLOCKED — preparation only.** Phase 8B has not passed the mandatory human/speech acceptance gate. No release candidate is certified and no new Phase 9 live rehearsal, reset, public release or real notification was performed.

Audit: 2026-10-10T11:43:34.950362+00:00. All seven prerequisite reports were inspected; latest actual Phase 8B per-call receipts and acoustic controls were checked rather than treating the prior summary as approval.

## Exact blockers

- Human-heard Bulgarian and English confirmations remain unverified
- Actual dashboard call/conversation/agent/tool/booking visibility remains unverified
- Telephone-band ambiguity/negative/question recognition safety has not passed
- Fixed-date Bulgarian synthetic telephone speech probes failed; fixed-date attended voice rehearsal not yet verified

Three selected-affirmative synthetic SIP business workflows passed in Phase 8B with distinct appointments and restart persistence. They are not three human-accepted calls. The owner reported an initial dashboard connection refusal; the intended port 3011 returned HTTP 200, but actual visual rows remain unverified. The Ivan telephone-band question control became affirmative in all three decode variants. These are mandatory failures; DEMO_READY_WITH_LIMITATIONS cannot waive them.

## Isolated preparation completed

Read-only readiness command, version inventory, fixed dated presentation plan, safe reset confirmation/seed preservation, disposable reset/idempotency/isolation tests, bilingual presenter scripts, customer-journey/recovery/checklist documents. Existing bounded two-second UI polling is retained; no dashboard redesign or new live event simulation was added. Bilingual templates are present; current tenant Email/SMS/WhatsApp connections are NOT_CONFIGURED. Four existing offline mock messaging scenarios were reproduced independently, not delivered or inserted into the live dashboard.

Fresh verification: 243 backend tests passed in 55.353 seconds. Frontend nine tests, lint, typecheck and build were rerun and passed. Source/secret checks are recorded in artifacts/phase9/final-checks.json when complete. No proprietary semantic runtime or paid voice provider was introduced. Backend reset safeguards are source changes for offline maintenance; they were not deployed to or exercised against the running database.

## Reproducibility inventory, not a release

Local preparation checkpoint: 40483dc479c3d1f362bd8961407df24877861956. Subsequent source changes must be reviewed/committed before freezing an RC. No release tag or remote push was created. Frontend's existing application version is 0.1.0; no independent backend release version is declared. RC identifier remains null while the mandatory gates are blocked.

Qwen: hf-1cfa9a7208912126459214e8b04321603b3df60c, Q4_K_M, SHA-256 9a91506f18e56bfa9389a939db1b36029daf8c49327b0eb0bc9e19d627b00e79. Original BF16 assets are untouched. STT: hf-536b0662742c02347bc0e980a01041f333bce120. TTS: BG38 3f6ca06b3ca78352eb00d8e96349c0bedaa3d2f1 and MioCodec 3a737f0de2c6324cb2fe40c1fbd1056c7add423d; Windows Ivan remains evaluation-only. Migration version: 5.

| Service | Running image ID | Runtime state |
|---|---|---|
| asterisk | sha256:a8f0e18a71b691507ce7c4973991451e9f6a5321ad5845884f9c3856598fade3 | RUNNING |
| qwen | sha256:33868c035b21dc63f7c60b7438774283fd99215bc319114eb03de5df4ce7cd6b | HEALTHY |
| stt | sha256:541f16e21879399e543e4462c58b11eec14195c39f9e84b184fe0b724c7b7afd | HEALTHY |
| tts | sha256:556b541f9d544fb0c84aebc90cd3d24bb94639bf204fafc346f7ed97a9df8920 | HEALTHY |
| backend | sha256:4ccfec95b00489192db129cb6c431acb9c42a98a0c62812bbf6629a08a80ba17 | HEALTHY |
| frontend | sha256:b7eeb6e6fca036130dbb474c110821a7e8e6f73eb0a1e7b778d3904ff337705a | RUNNING |

Pinned image references/model revisions and dependency/configuration hashes are captured in artifacts/phase9/version-inventory.json. Runtime image IDs are existing local images, not newly published immutable release artifacts. Python constraints, frontend lockfile and both Compose files are retained. This audit does not rehash all model weights; existing verified startup caches are preserved.

## Required next gate

Resolve the acoustic consent control failure, obtain genuine BG/EN listening and visual dashboard evidence, then repeat three consecutive complete SIP journeys. Only then freeze a reviewed source commit/configuration, build a dedicated RC, rehearse fixed dates/reset/restart and decide release readiness. Public-network calling, real clinic calendars, real notifications/payments, production identity/security/recovery/capacity remain separate unverified integrations.


## Latest prerequisite preparation

See [PHASE9_SAFETY_PREPARATION.md](PHASE9_SAFETY_PREPARATION.md). The initial Git checkpoint exists; the remaining blockers are human audio/dashboard acceptance, confirmation-mode selection and failed Bulgarian fixed-date speech probes. The optional keypad guard remains inactive and undeployed. Latest full suite: 243 tests passed in 51.418 seconds; frontend nine tests/typecheck/lint/build pass. No new live calls or reset were performed.
