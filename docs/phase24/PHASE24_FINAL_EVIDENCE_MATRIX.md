# Phase 24 Increment 1 — local evidence

14 October 2026. Increment 1 was explicitly approved against d71c08d. Only local setup/booking preview changes were implemented. **Phase 24 completion, UX GO and production GO are not established.** Website source is unchanged; no protected merge, push, infrastructure, model, telephony, real booking, email or customer-data action was performed.

## Before / after

Fresh pre-change isolated reproduction: Business 09:00–12:00, booking in bg-BG and en-US both FAIL, 0 bookings, because the request always used 15:00. After: both PASS, representative 09:00, one disposable booking per successful scenario. Existing calendar refusal rules were not edited. Search is bounded to 14 days; no suitable slot returns BLOCKED/preview_no_slot with zero bookings. This is a preview limitation, not proof that later dates are unavailable.

BG/EN scenarios cover booking, short confirmation, rejection, ambiguity, occupied slot and language switching. Additional tests cover three tenant timezones, holidays/closed days, unavailable periods, DST gap/fold, legacy optional fields, missing slot, replay and both-tenant data isolation. Same-event replay invokes each inbound turn twice and still observes exactly one CreateAppointment/booking. Existing full-suite privacy, ownership, permission, uncertainty and idempotency checks pass. The primary fixture tables for both tenants remain unchanged by preview; only redacted UX receipts/audit are intentionally persisted. Models/providers inside simulation are mock and disposable.

## Commands and final outcomes

From test_mid (PowerShell):

- `.venv/Scripts/python.exe -m unittest semantic_os.backend.tests.test_ux`: 27 PASS, 3.294s; artifacts/phase24/targeted-tests.txt.
- `.venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests`: 355 PASS, 48.988s; artifacts/phase24/backend-tests.txt.
- `.venv/Scripts/python.exe scripts/evaluate_phase17.py --output artifacts/phase24/evaluations.json`: corpus 1.4.0, 45/45 PASS; same versioned corpus/runner, mock token usage remains NOT_MEASURED.
- `.venv/Scripts/python.exe scripts/check_migrations.py --output artifacts/phase24/migrations.json`: schema 1–5, integrity, foreign keys and data preservation PASS.
- `.venv/Scripts/python.exe scripts/check_source.py`: source/config checks PASS (final count recorded below).
- `node semantic_os/security/scan-secrets.mjs semantic_os/backend semantic_os/frontend/src semantic_os/config scripts docs/phase24`: environment-secret comparison PASS; no fresh Gitleaks/hosted CI claim.
- In semantic_os/frontend: `npm run test`, `npm run typecheck`, `npm run lint`, `npm run build`: 39 tests PASS and all checks PASS; frontend-tests.txt/frontend-build.txt in artifacts/phase24. Native validation helper tests verify invalid focus, collapsed FAQ reveal, aria-invalid/error association and valid/no-form paths. Existing locale assertions include the new BG/EN status/error labels.
- In artifacts/phase13b/ontelyx: `npm run test`, `npm run test:config`, `npm run build`, `npm run format:check`: 72 Vitest + 6 Node tests PASS, configuration/typecheck/build/format PASS. No website source edits.
- `git -c core.whitespace=cr-at-eol diff --check`: PASS; locale CRLF preserved.

Execution failures corrected/retried: initial targeted assertions used UTC date instead of tenant-local date and a slot outside the 14-day bound; fixture assumptions were corrected without changing calendar rules. A Python default-encoding write truncated the test file; it was restored from HEAD and reconstructed with explicit UTF-8 before verification. Initial migration/website execution hit sandbox temp-file permissions (SQLite/ENOENT); authorized local reruns passed. An attempted discovery with `-t .` rejected the non-package tests directory; existing supported discovery above passed. Existing Starlette/httpx deprecation warning remains; no dependency scope expansion.

## Exact changed files

- semantic_os/backend/assistant/ux.py
- semantic_os/backend/tests/test_ux.py
- semantic_os/config/phase17_evaluations.json
- semantic_os/frontend/src/views/SetupView.vue
- semantic_os/frontend/src/services/setupValidation.mjs
- semantic_os/frontend/src/services/setupValidation.d.mts
- semantic_os/frontend/src/locales/bg-BG.json
- semantic_os/frontend/src/locales/en-US.json
- semantic_os/frontend/tests/setup-validation.test.mjs
- semantic_os/frontend/tests/workspace.test.mjs
- docs/phase24/PHASE24_ENTRY_AND_IMPLEMENTATION_PLAN.md
- docs/phase24/UX_JOURNEY_AUDIT.md
- docs/phase24/PHASE24_FINAL_EVIDENCE_MATRIX.md

## Compatibility, blockers and rollback

No API/schema/real-calendar changes; existing receipts retain their fields, and an additional localized diagnostic code reports bounded no-slot selection. Synthetic reference timestamps can change to the day preceding the selected slot; receipts expose the actual reference and timezone. Existing drafts without optional fields use existing calendar_base defaults. Activation remains explicit and gated; simulated test PASS does not verify live providers/voice.

Rendered browser/mobile/keyboard/screen-reader acceptance remains NOT TESTED here. Phase22 exit, actual voice/model/licensing/capacity, verified continuity, public staging scope, deployed DR and external pilot gates remain BLOCKED or NOT TESTED as previously documented. No new spending or extension of the staging host deadline. Competitor benchmark remains documentation research, not product parity evidence.

Rollback: revert only the Increment 1 commit on this feature branch (`git revert <increment-commit>` after reviewing its diff), then rerun the commands above. No database downmigration, provider rollback or external cleanup is necessary: real records and schema were not modified. Reverting restores the known fixed-15:00 preview limitation. Local source rollback is reviewable via git; no deployed rollback/DR claim. Final commit hash is reported in the user response, avoiding a self-referential document hash.

Stop after Increment 1. Any next scope requires separate explicit approval. No deferred voice/identity/scaling/DR work is authorized by this increment.
