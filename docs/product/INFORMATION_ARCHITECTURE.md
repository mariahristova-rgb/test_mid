# Navigation migration

11 October 2026. Local feature branch `codex/phase15-product-experience`; no Phase 15 push/merge/public deployment. Existing URLs and the two-agent runtime are retained.


Business Workspace currently groups existing Overview/dashboard, Conversations/inbox, Appointments and Assistants. Leads & Requests and Reports are planned, not fake navigation entries. Assistant Studio groups existing setup, testing, widgets, agents and channels. Operations groups existing diagnostics/operations, calls, integrations, Google, organization setup, billing, usage, settings and platform administration.

Code: frontend/src/services/navigation.mjs and .d.mts, App.vue; router/index.ts URLs unchanged. Groups are presentation only: every backend role/tenant check remains authoritative. Viewer sees four business routes. Operator sees tests and operations, not credential/configuration screens. Admin sees configuration; platform administration separately requires platform_admin.

Preserved routes include /dashboard, /inbox, /appointments, /assistants, /setup, /testing, /widgets, /google, /calls and /administration. No migration/delete/redirect changes. Locale labels exist in bg-BG/en-US. Native details/summary provides keyboard disclosure; current advanced group expands. Narrow navigation wraps rather than adding a horizontal nested scrolling strip.

Regression tests: navigation.test.mjs verifies uniqueness, all retained tasks and role distinctions. Actual browser acceptance remains open. Next changes require P0 acceptance before new business views.
