# Phase 15 product audit

11 October 2026. Local feature branch `codex/phase15-product-experience`; no Phase 15 push/merge/public deployment. Existing URLs and the two-agent runtime are retained.


## Evidence matrix

| Capability | Classification | Actual code / evidence | Next gate |
|---|---|---|---|
| Tenant/RBAC, persistent conversations and agent handoff | EXISTING_AND_VERIFIED | backend/assistant/{store,security,booking,orchestration,tools}.py; 296-test baseline | Existing coverage retained |
| Saved drafts, test receipts, immutable widget publish | EXISTING_AND_VERIFIED | backend/assistant/{ux,widget}.py; frontend/{SetupView,WidgetView}.vue | Browser publishing journey |
| Existing Inbox and three-pane metadata debugger | EXISTS_NEEDS_UX_WORK | WorkspaceView.vue, ConversationDebugger.vue; no second inbox | Synthetic browser takeover/queue |
| Queue assignment/revision and audited internal notes | IMPLEMENTED_UNVERIFIED (browser) | inbox_queue.py, InboxQueue.vue; four new unit tests | Browser check blocked by auto-review |
| Three navigation experiences | IMPLEMENTED_UNVERIFIED (browser) | navigation.mjs, App.vue; three role/route tests | Owner approved grouping; real mobile check |
| Google BG create/reschedule/cancel | EXISTING_AND_VERIFIED (named local test) | concierge.py/concierge_api.py; owner-authorized provider readbacks and duplicate replay | Broader traffic/concurrency not certified |
| English create/cancel | EXISTING_AND_VERIFIED (named local test) | booking 728ba8b8-c018-4db0-93e2-a1b5cd85317d-booking | Human inbox receipt open |
| Same-day reminder | IMPLEMENTED_UNVERIFIED | concierge.schedule/deliver; both test reminders cancelled correctly | Actual due delivery not run |
| Google account authorization | EXISTING_AND_VERIFIED | two connected records, primary owner read HTTP200 | Seven-day testing-token/reconnect limits |
| Public HTTPS website/widget integration | BLOCKED | public config rejects local/private hosted targets; no new staging endpoint | Owner requested endpoint, budget €10; provisioning prerequisites |
| Leads/request operator workflow | EXISTS_NEEDS_UX_WORK | concierge request records/admin API only | Assignment/follow-up view not implemented |
| Outcome funnel and quality coach | MISSING | Existing raw counts/diagnostics only | P1 blocked until P0 acceptance |
| Voice acoustics/consent | BLOCKED | Qwen/STT/TTS/Asterisk healthy does not imply accepted voice | Separate human-acoustic test |
| Real-device Web Vitals/a11y | BLOCKED | Watch Demo browser evidence is narrower than assistant acceptance | Browser security permission and representative devices |

## Repositories and chronology

Remote main: test_mid 4ddf9ee; ontelyx 40894dc, independently verified via git ls-remote. Earlier reports saying no pushes or no Google accounts describe earlier checkpoints and are superseded by the current source/status. The Phase14 local-check script's NOT_RUN means that script performs no Google mutations, not that the separately recorded approved lifecycle never ran.

Actual frontend is Vue3/Vite, not Next.js. The frontend AGENTS text describes Next.js; no Next runtime exists, so framework-specific instructions cannot justify a migration. Separate branches were created from the clean committed baselines. No proprietary import was found by check_source.py (216 files, zero failures).

Website entry is public config/iframe presentation only. Backend tokens, tools and SQLite remain private. Watch Demo's asset and 124-second behavior are preserved. Existing cloud services called ontelyx/ontelyx-frontend/ontelyx-inference and VM super-test-node are not treated as this independent assistant deployment.

Commands: git status/log/ls-remote; phase14_local_check.py (20 loopback GET samples); full unittest baseline and final suite; npm test/lint/typecheck/build; check_source.py. Evidence lives under ignored artifacts/phase15 and prior Phase14 receipts. No credential values or callback codes were copied into reports.


### Superseding checkpoint

Owner-authorized browser automation subsequently succeeded for the isolated synthetic Inbox only; the initial denial is retained in UX_ACCEPTANCE.md. Current verification is309 backend tests,29 frontend tests,227 source files/zero violations and source secret scan with no leaks. Six Google owner-login tests exercise signature/audience/issuer/email, nonce/PKCE, binding/replay/expiry, role revocation/tenant separation and HTTPS route cookies. No actual hosted login is claimed. Budget is now€2/week, superseding€10/month. Staging package and additive owner-only Google identity adapter are implemented, but resource creation is blocked at OAuth-scope approval; DNS/client callbacks remain owner gates.
