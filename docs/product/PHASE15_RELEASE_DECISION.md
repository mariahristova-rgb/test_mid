# Phase15 release decision

11 October 2026. Local feature branch `codex/phase15-product-experience`; no Phase 15 push/merge/public deployment. Existing URLs and the two-agent runtime are retained.


**BLOCKED.** The first P0 increment is local and regression-tested, not full Phase15 completion. Business/Studio/Operations grouping and Inbox metadata/notes are implemented. BG real reschedule/cancel and English real create/cancel provider receipts pass. Owner confirmed BG inbox delivery.

Mandatory gates still open: browser acceptance (automatic review denial), public HTTPS widget integration (endpoint requested, €10/month ceiling, durable storage/identity/DNS/cost plan required), English inbox receipt, actual same-day reminder, English reschedule and full lifecycle matrix. Voice remains blocked on independent human audibility and acoustic confirmation safety; healthy services do not change that status.

P1 health center, unified outcome dashboard, Leads & Requests operations, Quality Coach, failure-to-approved-regression and measured bottleneck optimization are planned, not implemented. P2 industry templates are gated behind P0/P1. No duplicate builder, inbox, orchestration or analytics database was introduced.

Next owner actions: scoped synthetic browser approval; confirm English messages; approve a concrete isolated hosting plan within the stated budget and supply/control a public DNS name. The existing cloud Ontelyx services and unrelated VM must remain unchanged. No Phase15 push/merge/public deployment has occurred. Local code can be reviewed with git diff and the file-level plan.


## Latest verified checkpoint

309 backend tests pass in86.112s;29 frontend tests plus zero-warning lint/typecheck and Docker builds pass;227 source files/zero boundary failures; redacted source scan2.46MB/no leaks. Approved synthetic browser checks verified assignment/awaiting status, audited note storage/reveal, human takeover/reply/resume, correct new human provenance, Bulgarian labels and no document horizontal overflow at all eight widths. Compact filter disclosure was verified in the final390px build. Old messages without provenance remain unchanged. Native browser zoom keys did not change the viewport, so200%zoom is NOT_VERIFIED; physical devices/screen readers/offline remain open.

Local browser metrics: desktop initial sampleLCP1412ms/CLS0/INP480ms; mobile/mixed-resize second sessionLCP1832ms/CLS0/INP992ms. Unthrottled synthetic automated sessions under concurrent Docker activity, not representative p75; no claim of meeting INP target. The local hook now distinguishes initial/reporting viewport and sends no telemetry.

Cloud status: no paid VM/IP/disk created. A dedicated service account exists with no project-wide roles and an accessor grant only on G_CLIENT_ID. Provisioning was rejected by auto-review due cloud-platform scope; official Google documentation and exact IAM evidence were checked. Explicit owner scope approval is pending. Revised ceiling€2/week; candidate72h compute stop plus retained staticIP/disk, estimated€1.9577/week with30%contingency and network reserve, no free tier assumed.

P1/P2 remain gated. Small local feature commits are authorized by the task; no Phase15 push, merge or public release is performed.
