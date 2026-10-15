# PostgreSQL runtime and worker acceptance
Status: PASS_LOCAL_RUNTIME for the explicitly tested bounded topology; not production/HA acceptance.

postgres_store.py subclasses existing Store. Business logic, tenant checks, approvals, idempotency, jobs and agents are reused. Psycopg 3.3.6 / pool 3.3.3, pool default/max 4/8, bounded waiters 16, connect/acquisition/lock timeouts, 10-second statement timeout. Connections are held for transactions and returned after materialized reads. No pool per request. close() closes the pool.

SQLite assumptions mapped explicitly: ? placeholders, INSERT OR IGNORE, reception-order rowid, JSON text extraction with typed quantities/booleans, UTC julianday/strftime, nested business transactions and append-only billing triggers. PostgreSQL identity cursors preserve reception order. Bootstrap derives columns, composite tenant foreign keys and unique constraints from existing SQLite migration definitions; PostgreSQL runtime migration version1 is separate. No customer SQL enters the translator.

Cross-instance writes take pg_advisory_xact_lock(26260001), preserving BEGIN IMMEDIATE exclusion. This deliberately serializes writers across the whole database; it is correct for a bounded staging topology, not a throughput claim. Process-local RLock is not the only exclusion. Customer jobs commit a claim/lease before provider writes, then reconcile running/uncertain work with GET only.

Actual disposable PostgreSQL17 Docker tests: 14/14, 72.502s, no skips. Existing BG/EN booking tests run against PostgreSQL; independent Store/worker instances claim once, lease expiry/recovery avoids another POST, tenant FK rejection, immutable ledger, failed transaction rollback, failed DDL rollback, DST and inbox SQL pass. Fixture uses real PostgreSQL and mock provider transport; no external accounts. Tests model connection/worker reconstruction, not a killed OS process or multi-region failover.

Synthetic measurements: 100 tenant reads p50 9.925ms / p95 16.687ms; 50 transactions across two independent Store instances p50 45.375ms / p95 66.273ms; all 50 increments persisted. Each pool used one connection, max2, zero waiters at sample. No cloud latency, peak connections or SLO inferred. Receipt artifacts/phase26c/postgres-runtime.json.

Configuration: ASSISTANT_STORAGE_BACKEND=postgresql, server-owned ASSISTANT_POSTGRES_DSN or _FILE, ASSISTANT_POSTGRES_POOL_SIZE. staging/production without explicit migrated PostgreSQL fails closed; no automatic SQLite fallback or startup migration. Current BackupManager SQLite backup rejects PostgreSQL explicitly. Use reviewed native PostgreSQL backups; application backup/restore API parity remains BLOCKED. Full app-wide PostgreSQL dialect and performance acceptance beyond tested paths, distributed fairness and OS crash rehearsal remain open.

References: [Psycopg pool](https://www.psycopg.org/psycopg3/docs/advanced/pool.html), [PostgreSQL locking](https://www.postgresql.org/docs/17/explicit-locking.html).

Strict TCP configuration additionally requires sslmode=verify-full; alternatively an explicitly reviewed /cloudsql/ proxy socket. A negative test proves unverified TCP is rejected before connection. Direct constructor injection is reserved for trusted composition/tests, not a public API.
