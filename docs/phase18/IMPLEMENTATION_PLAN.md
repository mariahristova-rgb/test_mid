# Phase 18 reviewed local implementation matrix

13 October2026. Owner requested execution after Phase17 validation/push, accepting the proposed local matrix. Preserve API/schema and existing feature branches. Phase17 source checkpoints: test_mid db939b7, website6175639;329backend/31frontend/78website tests and builds freshly passed. External Phase17 acceptance is still incomplete.

| Priority | Work | Files / acceptance |
|---|---|---|
| P0 | Bilingual synthetic Calendar lifecycle/reminder and uncertain-write regression | Existing test_google_concierge.py; verify persistence/provider fixture agreement and one write under replay |
| P0 | Consent refusal/revocation, expired sessions and retry continuity | Existing widget/booking tests; no privileged or duplicate action |
| P1 | Fail-closed evaluation corpus validation | Existing evaluate_phase17.py and versioned JSON; reject empty/malformed/duplicate/unsupported cases and skipped/loading failures |
| P1 | Executable iframe retry/reconnect/focus tests | Existing Node VM fixture pattern; no browser automation or external network |
| P2 | Evidence package and recovery/rollback checklist | docs/phase18; label synthetic versus unavailable external checks |

Modify runtime only for reproduced failures. No parallel agent/evaluation/billing implementation. Measure test execution separately from user/API/model latency; unavailable tokens/cost remain unavailable. Targeted tests first, full backend/frontend/website/source/migration checks before local completion. Rollback: revert Phase18 source checkpoint; no schema migration, deployment or data restoration required.

External gates remain: public browser approval/devices/screen-reader, live Google recipients/slots/cleanup/reminder, deployed DR and actual billing, pilot participants. Incremental spend€0; existing temporary host stop14October20:57Europe/Sofia must not be extended.
