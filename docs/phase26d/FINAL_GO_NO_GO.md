# Release decisions — Phase26D / Phase26E Gate 0

| Gate | Decision | Evidence / missing owner |
|---|---|---|
| Local process/PostgreSQL reliability experiments | PASS_LOCAL for executed fault suite only | Actual processes, independent recorder, SQL/catalog and second-instance restore. Full final regression in FINAL_EVIDENCE_AND_HANDOFF.md. No whole-app PostgreSQL certification. |
| Phase26D closure / Phase26E Gate 0 | NO_GO / BLOCKED_EXTERNAL_INFRA | No successful Phase26D exact-head CI; authoritative GitHub account payment/spending annotation. Observed full self-service journey also incomplete; human speech FAIL unresolved. |
| Limited private staging | NO_GO / BLOCKED_APPROVAL | No exact cloud resource/cost authorization, deployed IAM/routing/secret/backup/kill receipt. Mock Terraform plan is offline evidence only. |
| External provider / 3–5 business pilot | NO_GO | Dedicated empty test calendar consent/resource and exact action/cleanup approval absent; human and full journey acceptance missing. No owner primary-calendar access. |
| Public production | NO_GO / OUT_OF_SCOPE | No protected merge, enrollment, live payments or production deployment authorized. |

No automatic enrollment, resource activation, billing change, real provider call or main merge. No Phase26E branch or fabricated receipt. Human reviewer checklist and safe rollback are in STAGING_SECURITY_COST_AND_KILL.md and POSTGRES_FAILURE_AND_RESTORE.md. CI must be successful at the reviewed head before any release; no branch protection setting was weakened or changed.

## Safe acceptance continuation
The restricted continuation at c71b06a baseline added only tests/evidence on the same branch. New strict test at 36f3dd4 is FAIL in both languages: PG-USAGE-01 (usage history HTTP500 / SQLSTATE42803) and LOCK-SCOPE-02 (ownership GET under global advisory lock). Fresh40 booking/OAuth/native PG tests PASS_LOCAL_ONLY; the earlier445/14 receipts are preserved historical evidence. Browser DOM/keyboard/6 previews/resume passed bounded checks; spoken output BLOCKED_HUMAN, full browser journey/200% text zoom NOT_TESTED. Local release/Gate0 NO_GO now also has code findings, independently of BLOCKED_EXTERNAL_INFRA. No Phase26E implementation branch or production fix was introduced. See ../phase26e/END_TO_END_ACCEPTANCE.md and CI_AND_INDEPENDENT_REVIEW_CHECKLIST.md.
