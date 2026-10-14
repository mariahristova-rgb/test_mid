# Operator safety and incident proposal

Reuse Health/Quality/Operations,voice session/trace controls and existing redacted unknown/blocked job receipts. Monitor actual runtime health,active/failed sessions,tool/provider errors,backlog,pending approvals and capability status; no fabricated activity/human availability. Signed service identity/tenant is mandatory for voice transport.

Emergency rehearsal to review: disable relevant assistant voice channel/capability→new sessions denied→in-flight committed appointment preserved→pending approvals safely invalidated after work settles→redacted correlation/status verified→restore only after owner review/fresh sessions. Existing fixture timeout/interruption/termination/rollback tests are evidence for components; a new dedicated emergency-disable/deployed-restart rehearsal is NOT_TESTED in Phase23.

Unknown Calendar/Gmail/sending: preserve intent/job identity,no automatic reset/replay. Verify authorized provider state before manual reconciliation. Restart only scoped services after zero active/in-flight call checks; do not start all caches/models or copy customerDB. Source/image/data rollback needs approved compatibility and a new isolated restore target,not live overwrite. Incident owner/support contact remains NOT_ASSIGNED; no external notification sent without approval.

Stop for tenant breach,unauthorized/duplicate action,misdelivery,unintelligible critical readback,resource overload or deadline/budget violation. Preserve content-minimized evidence; default no raw recordings. Existing temporary host stop remains unchanged.
