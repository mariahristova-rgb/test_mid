# Persistence rehearsal and rollback
Docker Desktop is now available: 16 exposed CPUs, approximately 8 GB daemon RAM. Existing cruise containers were not changed. Only a purpose=test-mid-phase26b container was used, postgres:17-alpine from the existing cache, network none, no ports, 512 MiB memory, one CPU and tmpfs data. No image download or paid resource.

Run scripts/phase26b_postgres_rehearsal.py against a fresh labelled fixture container. It creates a new synthetic SQLite source with two tenants, Unicode/quoted contacts, conversations, appointments, jobs and messages. Composite keys/unique constraints and 83 foreign keys are translated; all table canonical checksums are compared after import and PostgreSQL pg_dump/pg_restore. SQLite backup integrity and checksums are checked separately. Receipt: artifacts/phase26b-postgres.json (ignored).

This is DATA PORTABILITY ONLY. Runtime Store still uses SQLite-specific transactions, json_extract, triggers/indexes, migrations and worker locking. PostgreSQL driver/pooling, distributed claims, immutable-ledger parity and autoscaling acceptance remain missing. No real database/token migration. Do not enable replicas or label this a production PostgreSQL migration.

Rollback: keep the original SQLite database authoritative; disable customer OAuth and live writes, stop creation admission, retain uncertain jobs for read-only reconciliation under reviewed access. Never blindly replay uncertain writes or delete historical audits. Revert feature commits after saving any newly created local records; no DDL changes in this increment. Fixture container can be removed only after exact label/network/port verification.

Final container sample: 87.44 MiB / 512 MiB, CPU 0.00%; this is a point-in-time sample, not peak usage. The verified labelled rehearsal container was removed after evidence collection. Existing user containers remain untouched.
