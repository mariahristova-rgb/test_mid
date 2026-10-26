# Invariants and planned fault matrix — written before test implementation
State machine (actual code): explicit visitor approval -> appointment pending_external + job pending -> committed running claim/60s lease -> one POST with stable event ID -> event receipt validated -> atomic confirmed appointment/completed job/outbound confirmation/reminder. Running/uncertain after restart -> GET only; missing/unknown event stays uncertain_external/uncertain. Definite pre-write denial -> blocked job/cancelled reservation. No automatic retry POST after uncertainty.

|Invariant|Positive oracle|Negative control / required detection|
|---|---|---|
|I1 at-most-once|Separate loopback provider DB records one POST/event after restart|Deliberately replay create in test oracle; count must detect >1 even if provider ID deduplicates|
|I2 truthful durability|Independent SQL status/IDs after process kill; pending not confirmation|Lost receipt must not project confirmed or lose job; intentionally wrong expected status fails|
|I3 tenant isolation|Two tenant datasets; direct SQL scoped row counts + API refusal|Wrong-tenant get/resource/job and FK must fail|
|I4 atomic ledger|Kill DB backend mid-transaction; rollback rows; restored append-only trigger|Raw ledger DELETE must fail; intentionally altered restore hash must fail|
|I5 consent precedence|Revocation before final write admission denies POST|Disconnect between availability and POST must prevent a not-yet-admitted write. Already admitted/sent write may have happened: record actual receipt, never replay; reauthorization needed for further provider reads|
|I6 recovery|Native dump into a different isolated PostgreSQL instance; SQL/catalog/hash checks|Tampered projection differs; original unrelated tenant/container unchanged|
|I7 deploy/cost|Offline plan/policy rejects public model/unpinned images/approval missing|Mutated policy inputs must fail; no assertion that alerts cap spend|
|I8 accessibility|Named human spoken transcript + focus sequence|DOM-only pass cannot satisfy human gate; historical FAIL retained|

Faults: kill before lease; exit after committed claim; provider success then process kill before persistence; provider accepts then HTTP timeout; two independent recovering processes after expiry; pg_terminate_backend in active fixture transaction; bounded statement/lock timeout, deadlock, pool exhaustion; disconnect while queued/in flight. Each receipt includes commit/time/environment, fault point, redacted before/after state, separate recorder POST/GET counts, SQL/catalog oracle, restart/exit/error classification and outcome. No production data or real provider calls.

The global advisory lock remains unchanged. Compare same-tenant and cross-tenant contention using fixed synthetic operation counts; measurements describe only this machine/workload. pg_verifybackup is not applicable to a logical pg_dump: use pg_restore --list, actual restore and SQL/catalog/hash validation instead.
