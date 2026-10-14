# Phase 25 — entry audit and proposed increments

Historical entry plan. Subsequent user approvals authorized the local catalog, reviewed additive connection API and provider/OAuth/entitlement/quote fixture implementation. See PHASE25_FINAL_EVIDENCE_MATRIX.md for current bounded status; the entry text below is not a completion claim.

14 October 2026. Design review only. Runtime implementation awaits separate approval. Entry: `codex/phase24-ux-readiness`, `c8506e39dbffe50570539ac1b9d0fd7086fea920`; worktree clean before this documentation.

## Verified entry state

Phase 24 Increment 3 evidence records 358 backend, 39 frontend, 78 website and 48 evaluation cases passing. These are prior-run results, not fresh Phase 25 test runs. Setup/mobile/keyboard acceptance is bounded synthetic evidence; screen-reader and zoom are user-attested. Phase 24 completion, public SaaS readiness and production GO remain unestablished.

Repository inspection confirms existing tenant-scoped Store, booking approvals, mock providers, Google OAuth state/binding/PKCE, encrypted secrets, billing ledger and server entitlement service. `google_workspace.py` pins expected account and login hint to the existing owner. `GoogleWorkspaceView.vue` is administrator configuration, not general customer self-service. Do not remove that owner boundary as a catalog change. Microsoft, Calendly and HubSpot self-service readiness is not established.

## Ranked task matrix

| Priority / increment | Proposed work | Exit evidence / approval |
|---|---|---|
| P0 A | Audit, architecture, security and proposed prices | This document and linked design; review required |
| P0 B | Local catalog, capability labels and explicitly simulated lifecycle states | BG/EN, keyboard, tenant/role and zero-network fixtures; separate approval |
| P0 C | Tenant-bound connection lifecycle contract and encrypted storage reuse | State replay, expiry, token rotation, revocation and cross-tenant tests; API/persistence review first |
| P0 D | General Google owner-authorized connector | Calendar discovery/resource permissions, scope checks and uncertainty fixtures; real account authorization separately |
| P0 E | Outlook adapter fixtures | Work/school versus personal/shared account capability distinctions; no live OAuth |
| P1 F | Calendly and narrow HubSpot fixtures | Plan/role limits, signatures/replay, mappings and duplicate recovery |
| P1 G | Connector entitlements on existing ledger | Server denial independent of UI; proposed packages only |
| P1 H | Custom integration scoping and quote UX | Separate subscription/maintenance; no payment or arbitrary URL executor |
| P2 I | Acceptance and final evidence package | Actual receipts, recovery/rollback and explicit remaining gates |

## Exact proposed first increment B

Reuse current integration view, router/RBAC and shared UI. Before approval, locate and review the final view insertion points; proposed affected paths are `semantic_os/frontend/src/views/GoogleWorkspaceView.vue`, `semantic_os/frontend/src/locales/bg-BG.json`, `semantic_os/frontend/src/locales/en-US.json` and existing frontend tests. A small static catalog module may be added under `frontend/src`; no backend endpoint, schema, token, calendar policy or billing change. Existing owner Google controls remain distinct from simulated customer connector cards.

Cards distinguish implemented owner-only integration from planned connectors. Planned providers show COMING SOON, never AVAILABLE or CONNECTED. Fixture lifecycle examples are visibly simulated and cannot start OAuth. Display current supported actions and limitations, not provider logos implying certification. Preserve deep links and role guards. Pricing remains proposed and cannot create checkout, invoice or subscription changes.

Extend existing tests rather than add a framework. Verify BG/EN labels, accessible names, keyboard interaction, clear simulation status, no connect action for unavailable providers and no external request. For later backend increments extend existing Google, SaaS, UX and versioned evaluation fixtures, including tenant isolation and unknown-write recovery. Run targeted checks after changes, then existing authorized full regressions before claiming completion.

Rollback B by reverting its local commit and rebuilding frontend; no database or provider cleanup. Later persistence/API changes require their own compatibility and rollback review. No protected merge or push is part of this plan.

## External gates

No new spending, OAuth app registration/publication, real customer credentials/data, live writes, payments, infrastructure, deployment, model downloads or telephony. Previous staging deadlines remain unchanged. Public OAuth verification, provider commercial permissions, real resource ownership, token revocation receipts and public acceptance remain external gates. No public SaaS GO.

See [architecture](SELF_SERVICE_SAAS_ARCHITECTURE.md), [provider research](PROVIDER_REQUIREMENTS_RESEARCH.md) and [updated proposed pricing](CUSTOM_INTEGRATION_PRICING.md). Remaining Phase 25 deliverable documents will accompany their reviewed increments; they are not asserted complete here.
