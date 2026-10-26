# Entry raw evidence â€” 26 October 2026
Starting SHA849d602aefdde6945fcbd3af51ab4711507dc9e5 equals fetched Phase26C origin head; clean worktree, no divergence. New branch codex/phase26d-reliability-gates. PR1 open/non-draft/unmerged, base main4ddf9ee, head c0cd760; PR2 draft/unmerged base c0cd760,head cbdc995; PR3 draft/unmerged base cbdc995,head849d602. Merge bases independently match these dependencies. No merges authorized.

[Exact baseline CI](https://github.com/mariahristova-rgb/test_mid/actions/runs/38707389720), job116330067725; raw logs inspected separately, not inferred from badge. [Baseline code](https://github.com/mariahristova-rgb/test_mid/tree/849d602aefdde6945fcbd3af51ab4711507dc9e5). Historical counts are leads, not fresh tests.

|Claim|Raw observation / method|SHA/environment|Oracle / state / owner|
|---|---|---|---|
|PostgreSQL serialization|postgres_store.py transaction takes pg_advisory_xact_lock(26260001), bounded psycopg pool|849d602/source|Code-only; real process/SQL faults NOT_RUN; engineer|
|Uncertain booking recovery|customer_booking.py running/uncertain branch GETs stable event ID, no POST|849d602/source|Process/independent recorder tests NOT_RUN; engineer|
|Production backup|backup.py explicitly rejects non-SQLite|849d602/source|Native logical restore drill required; app BackupManager remains BLOCKED|
|Live acceptance|external_acceptance.py disabled default, account/resource/approval binding; writes denied|849d602/source|No real approval or consent; BLOCKED_APPROVAL; owner|
|Cloud/model|Terraform unapplied, GPU unmeasured; no active host flags found|local flag names/known boolean values only|No cloud/account/secret access; BLOCKED_APPROVAL|
|Accessibility|Historical human FAIL: nothing spoken; no named reader/browser|Prior user report|Unresolved; manual BLOCKED_ENVIRONMENT|

Initial Docker daemon unavailable. Start installed Docker Desktop only, then verify actual local topology before creating named disposable resources. No credentials/customer DB read. All new provider traffic must terminate at a dedicated loopback mock recorder. Current code review includes Store/backup/OAuth/tool/worker/API/providers and relevant setup/widget/integrations/billing/locale paths; no new provider feature is planned.

## Runtime update — 26 October 2026
Docker became available after the owner started Desktop. Only two new purpose=test-mid-phase26d containers were used: test-mid-phase26d-pg (127.0.0.1:55426) and test-mid-phase26d-restore (127.0.0.1:55427), each 512 MiB / 1 CPU / tmpfs. PostgreSQL 17.11; cached postgres:17-alpine image digest b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24. Docker exposed 16 CPUs and 7,983,759,360 bytes RAM. Existing voice/inference/database containers were not changed or inspected for customer content.

The initial NOT_RUN rows above describe entry state, superseded only by the specific process/SQL/recorder receipts in POSTGRES_FAILURE_AND_RESTORE.md. They do not imply external acceptance.

Initial remote c9c38cda6665b6df8b76329b8588d5f40f587e05 omitted runtime fixes because these were still being tested locally. Local 5ebe2585399a25934be679a71179281d3c4c32cb commits both fixes and expanded tests/restore oracle. 88639af439e4244131bd8c0435aa3df84aec7698 separately refreshes certifi after a new audit advisory. No fixes were lost, reset or recreated from assumed reports.

GitHub check 121612762049 at c9c38cd independently returned: “The job was not started because recent account payments have failed or your spending limit needs to be increased.” There are no executed test steps/logs. Classify BLOCKED_EXTERNAL_INFRA, never PASS_CI or CODE_FAILURE. No billing setting was changed.
