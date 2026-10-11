# Publication lifecycle

Assistant drafts retain revisions, configuration hashes and isolated test receipts. Required tests depend on booking/FAQ configuration. Private activation requires administrator role, explicit consent, unchanged source/business/agent state, valid BG/EN config, required passing receipts, no active call and no pending approval.

Widget publication separately requires a published matching draft, current published business hash and enabled matching agents, verified email, nonempty instructions, active mock Web Chat configuration, approved bilingual FAQ entries, verified origins and valid booking tools when enabled. These checks return existing typed domain errors. They are demo promotion checks, not production provider certification.

A widget version contains its immutable config/settings, source draft ID and tenant calendar/agent signature. The integration holds a version pointer and monotonically increasing epoch. Runtime uses the snapshot; legacy instruction edits do not silently change published content. Shared scheduling/agent changes disable use until a compatible tested publication exists.

Saving widget settings or generating a new domain challenge unpublishes it. Publish, Unpublish, Rollback and Revoke invalidate prior session credentials. Rollback requires same integration/tenant, still-verified origins and unchanged business/agent signature. It restores the widget snapshot, not tenant-wide calendar policy. Revoke is permanent; it cannot be reversed by publish/rollback/challenge.

No model API key is distributed; there is no visitor API key to rotate. Publishing changes the epoch, expiring visitor capabilities. Secret-provider key rotation remains an authenticated server operation.

Unit/API tests verify epoch invalidation, immutable content, business/agent change rejection, permanent revoke, ticket replay and authorization. The local separate-origin HTTP journey verified Unpublish rejection and successful compatible Rollback. Browser lifecycle UX is not yet accepted.
