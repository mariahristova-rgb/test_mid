# Backup and disaster recovery

The existing SQLite database contains structured records and encrypted attachment/transcript/recording bytes. A consistent snapshot uses SQLite's online backup API under the local Store lock. Snapshot bytes and manifest metadata are separately authenticated/encrypted with a dedicated managed backup key. Provider/master encryption keys are not included as plaintext. Keep both key families in recovery custody.

Configured RPO/RTO defaults are **targets**: 86400/3600 seconds, not measured production guarantees. Backup interval, directory and retention are configurable. Explicit `ASSISTANT_BACKUP_ENABLED=true` enables maintenance snapshots; no production data is deleted at startup. Retention pruning is a separate authenticated operator action, limited to this manager's named snapshots. Upstream vendor media is not part of the local database and needs separate backup/erasure ownership.

```powershell
# Supply the managed backup key through the process/secret manager; never print it.
python scripts/backup_assistant.py backup --database .assistant-data/assistant.sqlite3 --directory artifacts/backups
python scripts/backup_assistant.py restore --directory artifacts/backups --filename assistant-backup-<id>.json --target .assistant-data/recovery-new.sqlite3
python scripts/backup_assistant.py prune --directory artifacts/backups
```

The CLI reads the live source in readonly mode. Restore rejects every existing database/WAL/SHM target, validates authenticated metadata/checksum, database integrity, foreign keys and supported migration version before writing a new database. A new Store applies only safe forward migrations. Do not overwrite the live database or downgrade applied migrations.

WAL rehearsal exposed SQLite deserialize's WAL-header restriction. The validation copy uses SQLite's documented rollback-format header values; the authenticated original is restored to disk. An on-disk WAL regression test and actual staging restoration now verify committed data. [SQLite online backup](https://www.sqlite.org/backup.html), [deserialize format limitation](https://sqlite.org/c3ref/deserialize.html), [MultiFernet key rotation](https://cryptography.io/en/stable/fernet/) are the primary implementation references.

The final observed local staging backup + restore drill took approximately **2.66 seconds** for the synthetic dataset, with messages, billing usage, integrity and foreign keys checked. This does not establish production RTO/RPO, offsite durability or regional failover. See STAGING_VERIFICATION.json for exact recorded evidence.

Recovery procedure: stop/drain workers and live delivery; choose an authenticated snapshot; restore to a fresh path; supply the appropriate app keyring; validate roles/tenant counts/ledger/drafts/media; reconcile jobs marked sending/uncertain; test readiness and synthetic flows; switch the managed database path under operator approval. Never replay uncertain external sends automatically after restore.

Operations owns scheduling, encrypted offsite copies, access policy, capacity/retention, key recovery, regular restore drills and upstream object backups. The repository has tested local snapshots/restoration; an offsite service and production-scale disaster rehearsal remain external gates.
