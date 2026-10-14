# Persistence and rollback gate
Current Store remains SQLite: BEGIN IMMEDIATE transactions, JSON payload queries, external-key uniqueness, tenant-scoped operations/events, jobs and encrypted vault. New refresh claims reuse this data model without migration.

Two file-backed Store instances prove refresh mutual exclusion and disconnect wins. This is not PostgreSQL migration, autoscaling or HA evidence. PostgreSQL implementation/isolated migration rehearsal remains pending; no replicas enabled.

Required migration rehearsal: audited query inventory and transaction translation; isolated synthetic export/import with per-tenant row checksums, external-key/foreign-key integrity, job/claim replay, backup/fresh restore and zero-loss checks; rollback to immutable pre-migration snapshot with traffic paused. Never dual-write without an accepted consistency protocol.

Rollback this increment: revert its feature commits or omit its optional server configuration. Default customer OAuth remains disabled. Before restoring data, stop workers and back up current state with the existing authenticated snapshot tooling; retain reconciliation/source safety refs. No data migration performed.
