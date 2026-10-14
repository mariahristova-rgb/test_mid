# Operator incident and recovery playbook

Local13October2026. Reuse Health/Quality/Operations, existing redacted conversation executions, Google settings, job backlog and widget lifecycle controls. Shared unresolved statuses now include dead_letter,uncertain,failed,delivery_unknown,blocked. No new API/schema or retry endpoint.

| State | Required response |
|---|---|
| Calendar delivery_unknown / mismatched event | Read correlation and original intent ID; verify authorized provider state/identity/times. Do not resubmit booking blindly. Immediate verified readback can reconcile create; unresolved cases need authorized manual review. |
| Gmail delivery_unknown | Provider may already have accepted. Preserve job/message identity; no reset/replay without approved reconciliation. Never claim inbox delivery. |
| Interrupted job remains sending | Could have sent before crash; do not auto-reclaim. Backlog exposes status, but elapsed sending watchdog and deployed crash drill remain unavailable. |
| Blocked/revoked integration | Verify tenant capability flag/connection; reconnect only with owner authorization. No unrelated account token migration. |
| Tenant/consent/ownership failure | Refuse mutation; retain redacted code/correlation, inspect permission policy without revealing private text. |
| Critical security/duplicate action | Disable relevant widget/capability, preserve evidence, notify approved incident owner through authorized channel. Do not send external notifications without approval. |

Disable/rollback rehearsal passed in isolated tests: unpublish denies admission, rollback requires fresh session and keeps booked appointment unchanged; old capability never revives. Object reconstruction and interrupted-sending tests confirm no automatic send. Encrypted restore targets a new path with integrity/FKs/no-overwrite. No deployedDR/worker crash or production rollback performed.

Code rollback: revert Phase19 checkpoint on feature branch; schema remains5 and wire keys unchanged. Do not undo Phase18 time/privacy guards. Deployment rollback needs separately approved compatible image/data plan; no release applied here.
