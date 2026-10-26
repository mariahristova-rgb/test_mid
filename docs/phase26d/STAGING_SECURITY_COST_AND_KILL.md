# Unapplied staging boundary and cost decision

PASS_OFFLINE only: Terraform 1.14.9, pinned Google provider 6.50.0, fmt/validate and three mock-provider plan controls. The test command is plan, never apply. Fixture apply_authorized=true is a mock test input, not an account approval. No GCP API deployment or paid inference occurred. CI now includes terraform test.

Intended path: browser -> authenticated application -> tenant/RBAC/tool authorization -> API service identity -> IAM-authenticated internal Cloud Run model. API -> private Cloud SQL over reviewed transport; API -> scoped secret references and non-public file broker/GCS. Widget origin remains separate from staff origin. Tenant admission is still application-authorized, not inferred from IAM alone.

Positive mock plan asserts internal model ingress, only API service-account roles/run.invoker, min=0/max=1 model allocations, private SQL with backup enabled, uniform non-public GCS ACL. Negative plans reject absent approval and mutable latest API image. No model allUsers binding is introduced. These prove intended configuration, not real deployed identity, routing, callback correctness, secret permissions, backup API or restore cutover. All cloud-runtime claims remain BLOCKED_APPROVAL / NOT_RUN. In-process inference admission is not a distributed per-tenant quota; multiple replicas are not accepted.

Approved new cloud spend: zero. Budget alerts are not spend ceilings. Historical 15 October estimate in ../phase26c/COST_CAP_AND_APPROVAL_REQUEST.md assumed GPU+CPU+RAM $1.04652/hour, API fully active $0.19079/hour and SQL compute $0.06755/hour. These are unrefreshed historical USD planning inputs, not current quotes, measured charges or approval. At these assumptions, one-hour compute-only exposure is about $1.30; 24-hour continuous compute about $31.32. Add disk/PITR/backups, GCS/model files and requests, egress, logs, artifacts, secret access, cold/warm residence, revision overlap and contingency. Unknown volumes/pricing make a finite total ceiling unverified; even stopping compute retains storage/network costs. Actual GPU latency, tenant capacity, TTFT and unit economics: NOT_MEASURED.

Before any cloud exercise require exact project/account owner, region/residency, image/model/tokenizer digests, API/model/SQL/bucket/service-account resource list, maximum duration, complete component prices and exposure, approved maximum spend, alert recipient, kill owner/deadline, retained-backup charges and rollback/cutover approval. Prior primary-calendar or €2/week discussions are not authorization for this phase. No approved cloud manifest exists.

Human-owned kill sequence (cloud drill NOT_RUN):
1. Disable new admissions and customer booking bindings through existing authorized controls.
2. Quiesce writers; preserve pending/running/uncertain records and external IDs. Never clear unknown as success.
3. Disable provider write gates; reconcile admitted outcomes only with current approved read authority, otherwise escalate.
4. Stop GPU/API allocations using approved account tooling; no billing modification or resource deletion here.
5. Take verified native PostgreSQL backup, restore to new isolated target, compare manifests/catalog/tenant/ledger/audit. Keep source intact.
6. Inventory retained SQL/disks/backups/buckets/artifacts/logs/network; verify actual meter cessation and ongoing residual charges.
7. Independent operator signs receipt before re-enable. Terraform validation does not test this cloud sequence.

Separate human review required: inspect final admission/revocation semantics, restored ledger trigger, no lock held over HTTP, default-disabled real adapters, raw-identifier redaction, secrets mounting, tenant file broker, one-process versus multi-instance limits, and cleanup ownership. Codex source review is not peer approval. No branch-protection settings or billing controls were changed; successful exact-head CI remains mandatory before release.

## Dependency regression
Fresh pip-audit found certifi 2026.7.22 / PYSEC-2026-4320, fixed version 2026.10.19. Minimal change updates the application, STT and neural-TTS lock pins together; only the local application virtual environment was updated. No speech/model packages or models were installed. Repeat application lock audit: no known vulnerabilities; optional speech environments were not executed. [PyPA advisory](https://github.com/pypa/advisory-database/blob/main/vulns/certifi/PYSEC-2026-4320.yaml), [upstream release](https://pypi.org/project/certifi/2026.10.19/). Browser trust/TLS checks were not disabled. Existing lockfiles lack complete package hashes, retained as a supply-chain limitation.
