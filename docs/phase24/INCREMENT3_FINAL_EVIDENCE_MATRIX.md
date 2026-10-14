# Increment 3 — final local evidence matrix

14 October 2026. The previously missing selectable lifecycle/provider scenarios are implemented and tested. Scoped local setup/preview/mobile/keyboard acceptance is PASS, with user-attested screen-reader and 200% zoom results. **This does not establish Phase 24 completion, overall UX GO, production readiness or production GO.**

| Capability | Result | Evidence / scope |
|---|---|---|
| Seven new preview scenarios | PASS synthetic | 14 BG/EN browser cases + 7 BG 320px cases; unit/full-suite assertions |
| Management permissions and confirmation | PASS synthetic | Same-conversation booking, unchanged before approval, cached approval replay; denied tools BLOCKED |
| Provider failure / unknown | PASS expected fault | One mock attempt; zero confirmed local records; no automatic retry by the runner; unknown remains unresolved |
| Out-of-hours / configured closures | PASS synthetic | Existing availability refuses request; missing closed-day precondition remains BLOCKED |
| Unsupported question | PASS mock fallback | Correct explicit locale; safe deterministic response; no tools or booking |
| Existing contracts / schema / tenant isolation | PASS scoped | Additive scenario enum; prior values retained; schema 5 unchanged; two-tenant side-effect invariants |
| EN keyboard setup | PASS observed | All seven steps, error correction, configured tools, preview suite, visible focus |
| BG mobile setup | PASS observed | All seven steps and bilingual required suite, actual 320px viewport |
| 320 / 390 responsive preview | PASS observed | 305/305 and 375/375 client/scroll widths; current BG/EN lang attributes |
| Field labels and target geometry | PASS sampled | Current review: 10 controls, zero unnamed; active buttons at least 44px high |
| Text/focus contrast corrections | PASS measured | Metadata 6.917:1; focus versus white 6.702:1; built styles verified |
| Screen-reader error / 200% zoom | PASS user-attested | User response: “И двете проверки минаха”; exact AT/version unspecified |
| Reduced motion | PASS source/current CSS observation | Existing preference rule; zero CSS animations/transitions observed; preference-toggle test NOT TESTED |
| Physical devices / full WCAG certification | NOT TESTED / not claimed | Browser geometry and human receipt are bounded acceptance evidence |
| Automated regression | PASS | 358 backend, 39 frontend, 78 website, 48 corpus; builds/source/schema checks |
| Live providers / voice / identity / production | NOT AUTHORIZED | No external writes, customer access, paid inference, telephony, schema change, deployment or main merge |

## Exact source/test files changed

- semantic_os/backend/assistant/ux.py
- semantic_os/backend/assistant/language.py
- semantic_os/backend/tests/test_ux.py
- semantic_os/config/phase17_evaluations.json
- semantic_os/frontend/src/views/SetupView.vue
- semantic_os/frontend/src/assets/main.css
- semantic_os/frontend/src/locales/bg-BG.json
- semantic_os/frontend/src/locales/en-US.json
- semantic_os/frontend/tests/workspace.test.mjs

Documentation: three new Increment 3 reports, supplemental SETUP_ACCESSIBILITY_REPORT.md evidence and a historical-note link in INCREMENT2_FINAL_EVIDENCE_MATRIX.md. Local ignored fixtures, builds, logs, JSON and JPEGs are evidence artifacts, not production services or a parallel evaluation system. The existing simulator/services and corpus are reused.

Rollback the local Increment 3 commit after diff review and rerun the listed regressions. No database downmigration or external cleanup is needed. Restoring the earlier enum removes the new scenario selections, and reverting CSS restores the measured contrast defects; neither action should be silently presented as acceptance. Final local commit hash is reported in the assistant response rather than embedded into its own commit.

The synthetic review page may remain open as a local deliverable for the user. Its data is disposable; no persistence or public hosting SLA is promised. Temporary viewport overrides were reset. No protected branch push/merge was performed. Remaining Phase 22/23 voice, verified continuity, live-provider, commercial model, cost and production infrastructure gates are outside this increment.
