# Data model and migration policy

The new database is isolated from existing workspaces. SQLite is the explicit fresh-development MVP baseline; it is not a conversion of the old semantic schema. Migration ledger versions 1 (assistant domain) and 2 (reminder jobs) are forward-only and idempotent. Existing legacy migrations/data were not executed, rewritten or deleted.

Phase 3 adds forward migration 3: call_events, call_participants, call_usage, voice_tickets, voice_transcripts and voice_recordings, with tenant ownership/conversation foreign keys and indexes. It adds missing lifecycle defaults to earlier assistant mock call sessions without overwriting their data/transcripts. New transcript/recording payloads live encrypted in tenant secret storage, referenced by expiry-bound metadata; old plaintext transcript disposition remains owner-managed.

Tenant: ID, display name, default locale, explicit time zone, message limit, retention and recording/transcript policy. Other repositories use composite `(tenant_id,id)` primary keys, tenant foreign keys, nullable assistant/conversation references, a tenant-unique external key, JSON domain payload and creation timestamp. JSON payloads are typed/validated at API/application boundaries; this is not a fully normalized production relational schema.

| Table | Main domain fields / relationships |
|---|---|
| users | Verified subject, role, enabled, preferred UI locale; subject external-key unique within tenant |
| assistants | Name/description/instructions, channels, both locales/default, LLM/voice settings, assigned agents, allowed tools, escalation rules/status |
| agents | Stable key, both locales, instructions, enabled, allowed tools |
| channel_connections | Assistant FK, channel/provider/state, server-side service membership ID; secret lives encrypted separately |
| contacts | Name, explicit address identity, preferred locale, SMS opt-out |
| conversations | Assistant FK, channel, optional contact reference, active locale, status/human escalation |
| messages | Conversation composite FK, normalized message contract, detected locale, direction and delivery metadata |
| call_sessions | Conversation FK, voice locale/state/events and opt-in synthetic transcripts |
| agent_executions | Conversation FK, handoff, correlation/status/time |
| tool_executions | Conversation FK, tool, arguments/outcome, approver, correlation; unique execution identity |
| appointments | Aware start, duration, contact name, originating conversation, locale, tenant zone, status |
| follow_up_tasks | Title/reason, optional due date/conversation, locale/status |
| provider_events | Connection/channel-scoped event external key, result/fingerprint, timestamp; inbound/callback deduplication |
| notification_templates | Locale/key/body; locale+key tenant-unique external key |
| usage_records | Messages/channel/provider, optional SMS segments/cost units, correlation; no invented live price |
| approvals | Conversation FK, tool/validated args/fingerprint, requester, locale, expiry/status and original result |
| audit_events | Actor/action/resource/correlation/status/time; never raw credentials or request body |
| secrets | Tenant/name-unique encrypted ciphertext; configured Fernet key, no raw value in APIs |
| jobs | Conversation FK, appointment reference, kind, due/status/attempts; unique reminder identity |

All tables have tenant/history indexes. Composite database FKs protect conversation/message/call/approval ownership and assistant/conversation links. Contact, service-user and appointment reference ownership is checked server-side; some references remain inside JSON rather than database FKs. Every repository read/update includes tenant scope. SQLite writes serialize in a single transaction, preventing overlapping appointment creation and duplicate mock actions. The store rejects legacy workspace paths.

Core Phase 2 adds a typed `booking_state` to existing conversation JSON: reference_at, timezone snapshot, active locale, resolved starts_at, duration/contact name, stage and approval ID. Natural booking approvals retain their date reference/timezone and correlate executor handoffs with the tool result. Assistant configuration adds booking_duration_minutes with a default of 30; older records receive defaults on API reads. These are additive fields with no destructive schema migration.

Retention is explicit: redact expired message bodies/attachments without deleting ownership/audit records. Existing backups/data/encryption files remain protected. Complete subject deletion, recording-byte storage, long-term audit/tool/contact retention and data export are deployment policy and implementation work before processing real sensitive information. Encryption covers configured channel secrets, not the entire SQLite database; use encrypted volumes and restricted file access for real data. Key rotation currently requires a managed migration; do not replace an existing key casually.

Scale boundary: single process/persistent volume. APIs currently return tenant-scoped lists without pagination. A production database adapter must provide the same tenant isolation, transactional idempotency, uniqueness, ownership and conflict behavior, with tested forward migrations and backup/restore. No automatic table drops or production data cleansing are authorized by source removal.
