# Phase24 entry audit and proposed local implementation

13October2026. Read-only audit/research/reproduction first; runtime changes awaiting reviewed approval. Starting clean branch codex/phase23-pilot-preparation at66e5f5f; website d7fab0b unchanged. Phase23was preparation only,not a live pilot. Phase22exit/verified-continuity/model/browser/DR/participant gates remain incomplete.

## Evidence and highest-impact reproduced gap

Phase21full351backend/37frontend/41corpus and Phase23fresh73fixture tests are dated synthetic evidence. No live pilot,real-model BG/ENquality/current latency/capacity,billing or deployedDR retrieved. Continuity contracts are proposed,not implemented/approved. Existing Vue/FastAPI,calendar/jobs/tool/consent/idempotency and owner views are reused.

Fresh disposable UX reproduction: valid Business09:00–12:00→TestStudiobookingBG/ENbothFAIL,0bookings,because simulate() always asks15:00. Calendar refusal is correct. Evidence artifacts/phase24/setup-baseline.json; no customerDB/provider access. This blocks valid owner configurations from mandatory test/publication; fix preview preconditions without weakening actual availability.

## Proposed first local increment to review

| Priority | Change | Exact affected files / reuse |
|---|---|---|
| P0 | Generate deterministic synthetic booking sample inside configured hours/open dates; show actual chosen reference/timezone | backend/assistant/ux.py simulate(),calendar.py existing availability; backend/tests/test_ux.py; no booking-engine rewrite |
| P0 | Save/Continue validation and accessible feedback for currently editable controls,focus/error association | frontend/src/views/SetupView.vue,existing locales,BusinessSchedule helper/frontend tests; server validation stays authoritative |
| P1 | Keep draft/tested/activated/mock scope and latest result/source config clear in existing preview | SetupView.vue,existing test receipts/readiness/EmptyState as applicable; no live preview/microphone start |
| P1 | Freeze synthetic acceptance scenarios and evidence; add reviewed regressions to same corpus | config/phase17_evaluations.json,scripts/evaluate_phase17.py/current tests; no parallel evaluation layer |

Preview selection must be bounded/reproducible,recognize holidays/unavailable periods and timezone/DST,seed occupied scenario at the selected slot,declare no available representative slot truthfully,keep BG/EN/rejection/ambiguity/idempotency expectations and isolated state. Old draft/schema/API keys preserved. Update the existing closed-date fixture expectation to validate a representative open-day preview while separately asserting closed-day refusal; do not turn an unavailable real slot into success.

Test order: reproduce regression→targetedsetup/calendar/frontend→BG/ENscenario/old-draft/tenant/unsupported/no-slot/side-effect negatives→existing fullbackend/frontend/website/source/migration/corpus checks. No real booking/send/provider/model/DBmigration or new public contract in this first scope. UI browser/device acceptance remains separately scoped; Node/compile results cannot certify usability.

## Deferred architecture and approval gates

Cross-channel proof/public JSON design awaits separate Phase21review; no callerID/string merge. Voice console/real mic/model/load/latency/capacity need explicit existing-runtime/device/benchmark scope and baseline before optimization; no paid API/download/WSL/replica. Production persistence/distributedqueue/locks,DR/SLO,current costs and source-to-image attestation need separately reviewed design/execution. Public launch/telephony/Google/customer/payment/analytics/protectedmerge prohibited.

Rollback: isolate approved source increment on feature branch,revert onlypreview/form changes,preserve Phase18provider/time/privacy guards,tenant DB/cache and revoked/committed actions. No schema or deployment means no downmigration/live restore. Incremental infrastructure authorization€0; historical hosting estimates not current bill; recorded14October20:57Europe/Sofiahost stop unchanged.

Phase24completion/UX GO/production GO not claimed. Remaining requested22deliverables will attach actual approved implementation/acceptance evidence and reuse previous architecture/recovery reports; this entry/benchmark is not substitute for missing gates.
