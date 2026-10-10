# Demo reset and repeatability

DEMO_BLOCKED. Preparation changes were tested only on disposable stores. The live tenant and all Phase 8B booking/audit evidence were preserved; no Phase 9 operational reset was performed.

The marked tenant is smilecare-demo, marker testmid-smilecare-synthetic-v1. Reset rejects other/unmarked tenants, production mode and active calls. It archives demo-created confirmed appointments, pending approvals/jobs and closes demonstration conversations. Required seeded_fixture appointments remain confirmed. It keeps assistants, both dentists, templates, seed customers and execution/audit/usage records. Repeated reset creates no new tenants or appointments; seeding an existing marked tenant does not duplicate data.

Before an owner-authorized reset: save the acceptance artifacts, verify zero active calls, and stop only the dedicated demo writer/services. Never invoke host SQLite maintenance concurrently with Docker's writer.

```powershell
powershell.exe -NoProfile -File scripts/demo/stop-local.ps1
powershell.exe -NoProfile -File scripts/demo/reset-demo.ps1 -Confirm
powershell.exe -NoProfile -File scripts/demo/start-local.ps1 -NeuralVoice
powershell.exe -NoProfile -File scripts/demo/readiness.ps1
```

The wrapper requires -Confirm before any maintenance and checks scoped services are stopped. A failed Docker query now refuses reset before database access; it cannot be treated as an empty stopped-service list. Direct CLI requires --confirm and a dedicated .assistant-data database. Prefer the wrapper; the direct CLI does not prove every possible separately launched writer is stopped. Do not run these destructive/archival steps merely to obtain a green report. No database deletion or volume removal is required.

The runtime's available slots are computed from seeded weekday/resource policy; they are not pre-booked placeholder appointments. The fixed demo-plan.json date must still be future and free. Existing historical seed fixtures retain their original date; reset does not silently move dates. After a permitted reset/restart, verify two seed fixtures remain, old demo-created appointments are cancelled, conversations are closed, audit retained and no duplicate seed was created. Live reset/restart rehearsal remains NOT_PERFORMED until Phase 8B passes.
