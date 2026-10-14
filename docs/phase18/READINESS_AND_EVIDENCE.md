# Phase18 capability and exit evidence

13October2026. **Authorized local scope complete; external pilot NO-GO.** Phase17 source was validated and pushed before this increment. Public/live acceptance is not silently complete.

| Capability | Local verdict | Evidence / external limitation |
|---|---|---|
| BG/EN two-agent booking/context/FAQ | PASS synthetic | Existing booking tests and corpus grounding/context cases; no real model-quality certification |
| Calendar create/reschedule/cancel + reminders | PASS synthetic | New bilingual full lifecycle asserts provider fixture/internal records, locale subjects, cancellation and replay |
| Unknown Calendar/Gmail responses | PASS synthetic | Committed POST timeout reconciles by stable ID once; unobservable write remains unknown and blocks replay; Gmail unknown not resent |
| Ownership/consent/tenant isolation | PASS synthetic | Forged/expired capability, mismatched recipient, refusal, revocation and concurrent intent regressions |
| Chat privacy | PASS targeted | Traces and uncommitted booking memory erased on clear/retention; appointments preserved; no full upstream erasure claim |
| Reconnect/expiry/handoff | PASS synthetic | Executed iframe code in Node VM: explicit retry same event/payload, no replay after expiry, human pause, consented clear; existing database reopen test |
| Backup/disable/rollback | PASS isolated | Existing encrypted restore and publication-epoch rollback tests are executable corpus cases; deployed rehearsal absent |
| Mobile/screen-reader/public browser | BLOCKED | Node VM is not layout/device/a11y acceptance; previous public scope approval unanswered |
| Real staging Calendar/mail/reminder | BLOCKED | No new connection, writes or sends authorized/executed |
| External customer pilot/voice/payments | BLOCKED | Separate acceptance and owner scopes required |

## Final executed checks

- `.venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests`:342PASS,49.559s; `artifacts/phase18/final-backend-tests.txt`.
- Targeted Google/widget/runner:45PASS,8.058s; iframe Node tests4PASS.
- `scripts/evaluate_phase17.py --output artifacts/phase18/final-evaluations.json`:32/32PASS, corpus1.1.0, synthetic only.
- Frontend `npm test`,typecheck,lint,build:35PASS and all checksPASS. Website unchanged runtime: fresh13OctoberPhase17validation78PASS/config/typecheck/build.
- Source240files/0failures; environment-secret293filesPASS; migration versions1–5/integrity/FKs/data preservationPASS; no schema/API changes.

No fresh hostedCI, dependency audit, Gitleaks, physical browser, real provider or cloud billing result inferred from these checks.
