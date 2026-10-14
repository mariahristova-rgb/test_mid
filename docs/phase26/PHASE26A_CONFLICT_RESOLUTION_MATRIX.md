# Semantic conflict resolution matrix
| File | Resolution and retained behavior |
| --- | --- |
| backend/assistant/api.py | Retain incoming customer workspace registration alongside current connector service registration. Fixture connectors require explicit fixture flag, development demo mode and non-strict environment. |
| frontend/src/App.vue | Combine role-aware navigation, mobile toggle and Google owner login with ordered tenant-scoped locale saves, stale-profile protection and retry UI. Remove obsolete parallel locale writer. |
| frontend/src/assets/main.css | Retain shared control geometry, action links without underline, responsive credential forms and readable bubble diagnostics. Preserve mobile menu and focus/reduced-motion rules. |
| frontend/src/locales/bg-BG.json | Union incoming keys with current changed/new translations relative to merge base. No duplicate JSON keys. |
| frontend/src/locales/en-US.json | Same semantic union; retain new UI translations and incoming localized connector/inbox/onboarding states. |
| frontend/src/views/SetupView.vue | Preserve optional business/contact/holiday/unavailable-period fields and accessible Save/Continue validation. Preserve five visual groups over existing seven persisted steps, forward/back adjacency and bounded local FAQ import. |
| frontend/src/views/WorkspaceView.vue | Preserve incoming operational metrics/inbox queue/role logic and current styled assistant actions, New draft route and concise dashboard readiness guidance. Remove duplicate legacy assistant card fragment. |

Paths above are relative to semantic_os except the explicitly prefixed backend/frontend names. API/DDL contracts are retained. Conflict-free incoming orchestration, calendars, jobs, consent, widget and Store changes remain in the merge and are included in full regression.

