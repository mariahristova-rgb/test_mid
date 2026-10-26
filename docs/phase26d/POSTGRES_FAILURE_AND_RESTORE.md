# Executed local fault and restore evidence

Evidence class PASS_LOCAL_RUNTIME, not provider/cloud acceptance. Windows 11 build 26300, Python virtual environment, PostgreSQL 17.11 in two independent Docker containers; topology and limits in ENTRY_RAW_EVIDENCE.md. Only synthetic demo/other tenants in unique fixture_<uuid> schemas. Separate durable loopback HTTP recorder stores provider events and counts every POST attempt independently of the application database and worker process.

## Reproduction and correction
Before correction, disconnect after FreeBusy still produced one POST and confirmed appointment; expected zero. Statement timeout after an uncommitted contact write leaked psycopg.errors.QueryCanceled. Original assertions and redacted trace are retained in artifacts/phase26d/before-fix-failures.json. Both failures were reproduced on actual PostgreSQL, not fabricated exception mocks.

customer_booking.py now commits final write admission after rechecking claim, connection revision/resource/consent, actor/tool permission, assistant/channel and handoff. The committed write_admitted_at is the linearization point. A disconnect before admission denies POST. A disconnect after admission may race an already admitted request: its real receipt/uncertainty is preserved; it cannot promise cancellation of an in-flight request. Correction from safe acceptance: the create POST is outside the transaction, but ownership GET in final admission holds the global advisory lock. See ../phase26e/END_TO_END_ACCEPTANCE.md (LOCK-SCOPE-02). Revoked uncertain jobs remain unknown without unauthorized GET or POST. Reauthorization/escalation is required.

postgres_store.py maps operational query/transport/acquisition failures to existing redacted provider_error/503 and retains transaction rollback, bounded pool and global advisory lock 26260001. Schema and public contracts remain unchanged. Native BackupManager PostgreSQL API parity remains unsupported; use the reviewed native logical runbook only.

| Experiment | Independent observation / result |
|---|---|
| Kill before lease | OS exit 90; pending survives; normal restart creates exactly once |
| Kill after committed claim | OS exit 91; running survives; GET 404 yields uncertain, zero create POSTs |
| Provider success then death before receipt | OS exit 92; two recovery processes; one POST/event, GET-only confirmation |
| Timeout after durable provider accept | Independent event committed before delayed reply; uncertain then GET-only confirmation |
| Disconnect before final admission | Separate recorder thread revokes during availability; zero POSTs |
| Disconnect after admission | One accepted event; truthful receipt, subsequent authorization denied; no replay |
| Revoked uncertain intent | No unauthorized reconciliation GET or repeated create |
| Removed calendar ownership | Final admission denies create |
| Statement timeout | Actual pg_sleep cancellation; controlled 503 and direct SQL rollback |
| Backend termination | pg_terminate_backend on owned fixture PID only; uncommitted booking transition rolls back |
| Pool and advisory lock exhaustion | Bounded acquisition/lock timeout; controlled domain errors; connections returned |
| Deadlock | Opposing raw SQL locks in fixture only: one SQLSTATE 40P01, one commit; Store global lock retained |
| Independent restore | pg_dump exported snapshot, pg_restore --list, new PostgreSQL instance; all table/catalog hashes equal; ledger deletion rejected; uncertain intent reconciles once |
| Serialization measurement | Two processes, 20 committed synthetic operations per trial; not a capacity/SLO benchmark |

Initial expanded suite: 14 tests PASS, 265.891 seconds. First complete suite: 445 PASS, 549.136 seconds, zero skips. Final exact-source rerun after certifi update is recorded in FINAL_EVIDENCE_AND_HANDOFF.md; do not substitute these earlier figures for it.

## Restore oracle and limitations
A repeatable-read exported snapshot couples pg_dump to the exact independently hashed table projection. Compare every table including native row identity, both tenants, SQL catalog foreign keys/checks/indexes/trigger definitions, and immutable ledger counts. A deliberately altered jobs content hash must fail comparison. Raw DELETE against restored ledger must raise IntegrityError and retain its complete pre-delete count. The source running job is left unchanged while the second instance reconciles by GET.

Measured dump/restore durations and checksum are in the committed LOCAL_RUNTIME_RECEIPTS.json summary and ignored full fault receipt. Zero acknowledged snapshot records lost applies only to this consistent snapshot drill; post-snapshot writes are not covered. Restore+SQL validation time excludes operator response and application restart: not production RTO or HA/DR certification. pg_verifybackup is inapplicable to a logical dump; pg_restore --list plus actual restore/catalog/content validation are used instead.

Owned PostgreSQL server logs independently contain statement timeout, administrator connection termination and deadlock signals (artifacts/phase26d/database-server-oracle.json). Raw database dumps and encrypted synthetic grant material remain ignored, never committed. No customer credentials or events were used.

## Reproduce safely
Use two cached postgres:17-alpine containers labelled purpose=test-mid-phase26d, loopback ports 55426/55427, database phase26c_fixture. Set PHASE26C_PG_DISPOSABLE=true, PHASE26D_PG_DISPOSABLE=true, the two explicit fixture DSNs, PHASE26D_SOURCE_CONTAINER and PHASE26D_RESTORE_CONTAINER. Run `.venv/Scripts/python.exe -m unittest semantic_os.backend.tests.test_phase26d_faults -v`, then full discovery. Tests reject other database/port/container identities and use fresh schemas; never point this harness at an existing datastore. CI declares its own two isolated services. Default-skipped means BLOCKED, not a PostgreSQL PASS.

Rollback: disable new customer-booking admission first; quiesce the maintenance worker; preserve jobs, stable event identities, ledger/audit and uncertain receipts. Revert application commits only on a review branch. Never replay an uncertain POST or downgrade to stale SQLite after PostgreSQL writes. Restore only into a new owned target and verify before any approved cutover; no automatic production cutover exists here.
