# Phase21 proposed incremental plan and approval matrix

Updated13October2026: owner approved first local B increment plus fixture voice/regression tests. Completed checkpoint:351backend/37frontend/41corpusPASS; see NO_CODE_BUSINESS_SETUP.md and PHASE21_FINAL_READINESS_MATRIX.md. Continuity contracts,model/service start and remaining increments are still pending. The original proposal below is retained for scope; it is not a full completion claim.

13October2026. **Awaiting owner review before runtime changes.** Target: owner configures one shared authorized assistant; website/mobile/voice/email use the same knowledge,booking,consent and operator state. Configured/live/mock/blocked states must remain explicit.

## B — No-code owner configuration

Reuse ux.py Business/DraftInput,revisions,readiness/test publication,SetupView.vue,WidgetView.vue and i18n. Proposed files: semantic_os/backend/assistant/{ux.py,calendar.py,providers.py},backend/tests/test_ux.py,frontend/src/views/SetupView.vue,frontend/src/services/i18n.ts and existing frontend tests. Extend bounded optional business description/contact,holiday/unavailable periods and single-service price metadata; validate and enforce supported schedule restrictions in mock calendar before displaying them as active. Keep complex catalogue/cancellation policies explicitly incomplete until their executor behavior is implemented. No payments,voice/live channel auto-activation. Preserve tenant-wide calendar warning and explicit publish action.

Contract gate: optional Business JSON/API fields and calendar-policy projection need reviewed approval; DDL stays schema5. Existing clients/drafts must load with defaults. Multi-service/tool argument changes and multi-owner Google support need a later reviewed design, not silent expansion.

Acceptance: synthetic owner save/leave/resume,BG/ENknowledge/hours/duration/holidays,tenant isolation,invalid values,unchanged old drafts and no external activation. UI/browser acceptance remains scoped separately; tests alone cannot claim a human completed the UI.

## C — Verified cross-channel foundations

Reuse contacts/contact_links,conversations,operations_events,existing proof/secret patterns and booking_state. Files: proposed backend/assistant/continuity.py with approved register hook in api.py; existing messaging_api.py,privacy.py; new synthetic continuity tests. First review explicit request/response contracts and purpose-bound proof lifecycle. Proposed operations: challenge→confirm→offer minimal unfinished context→explicit continue→revoke/unlink. Auth binds tenant,source/destination session,verified subject,scope,expiry,nonce and consent; never accept a client `verified` boolean or matching name/email/phone as proof.

Store bounded metadata/proofs in existing JSON/event structures if approved; no new DDL/customer database. Do not make the current operator evidence-link a customer credential. No raw-history copy; only permitted neutral booking intent/date/duration/reference context. New channel rechecks availability and asks fresh confirmation; committed/unknown actions must not be repeated. Production proof delivery stays disabled; offline fixtures only. Endpoint/public capability and retention contracts require owner review before implementation.

Acceptance: website↔mobile/voice/email synthetic linking,identity/tenant mismatch,expired/replayed challenge,refusal/revocation/concurrent sessions,minimal context,stale availability and uncertain action. Channel availability does not authorize identity disclosure or follow-up email.

## D/E — Reuse offline voice pipeline

Existing voice.py,voice_gateway.py,voice_stream.py,asterisk.py,rtp.py,audio.py,speech adapters/neural_voice.py and existing CPU compose remain the pipeline. Extend test_self_hosted_voice.py,test_voice_integration.py,test_phase8b_confirmation.py with fixture VAD/ASR/TTS and deterministic agents/tools; no second assistant. Verify final-only ASR,barge-in/epoch cancellation,bounded buffer/backpressure,timeout/disconnect,negative/ambiguous consent,repeat confirmation and committed booking persistence during playback interruption. No call recording/raw audio persistence by default.

Actual existing-model/speech worker start,benchmark and listening require separate scope after memory feasibility. Current free RAM2.86GiB/Docker7.44GiB; do not start all models or change WSL automatically. One synthetic session,existing cache/no downloads,CPU/no assumedCUDA proposed. Preserve cache digests and generic reference; no voice cloning. Telephone numbers/trunks/live calls/public SIP remain forbidden.

## F/G — Operator/evaluation and regression

Reuse CustomerWorkspace,Inbox,Operations and existing corpus/runner. Add reviewed cases for continuity/voice/no-code,not a new framework. Redacted codes/correlation/locale/channel; no raw transcript/audio or invented usage. Targeted tests after each increment,then full backend/frontend/website/source/migration checks. Record exact fixture versus model/listening evidence and cost scope.

Rollback: isolated Phase21feature branches after approval,small local checkpoints,revert only corresponding increment; schema5/data/model caches preserved. No deploy/main merge/push or paid resource. Contract rollback must retain compatibility with already saved optional fields and revocation receipts.

## Approval matrix

| Action | Required decision |
|---|---|
| Read-only source/hardware/license audit and this plan | Requested audit performed |
| B optional business contract/UI + deterministic tests | Awaiting owner review/approval |
| C verified continuity public/proof contracts + local fixtures | Separate explicit contract review before runtime implementation |
| D/E/G fixture-only voice/evaluation tests | Awaiting reviewed local implementation scope |
| Installed-model execution/services/restart/listening | Separately scoped approval; no inference/start done |
| Large downloads/system installs/WSL change | Not authorized |
| Live Google/email/customer/telephony/public browser/deploy/spend/protected merge | Existing gates remain closed |

Incremental infrastructure spend€0. No fullPhase21completion or production/real-time claim at this audit checkpoint. Remaining requested13deliverables will be completed alongside approved increments; this audit/comparison/plan is not substitute acceptance.
