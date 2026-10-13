# Calendar/Gmail and full booking lifecycle acceptance

All Phase18/19 actions here use synthetic identities and httpx.MockTransport. No owner Calendar event or mail sent in these phases. Historical live BG/EN evidence remains in earlier reports; public staging lifecycle, EN live reschedule/human mail receipt and real reminder acceptance remain BLOCKED.

Executable cases: bilingual availability→verified email→explicit booking→one provider event/local appointment→localized management/reminder→reschedule→cancel; duplicate action replay; same/different concurrent keys; fresh availability; Sofia/DST/cutoff; signed management ownership; information request verification/public links; refused consent/revocation; provider-time mismatch; committed POST timeout immediate stable-ID reconciliation; unobservable Calendar write/uncertain Gmail no replay; worker reconstruction and interrupted sending; disable/rollback session recovery.

Fixtures assert internal appointment/provider event consistency. Provider-time mismatch raises delivery_unknown before local success; unknown intent now has one redacted tool receipt with correlation/intent ID. Recovery does not create a second event. Gmail `sent` means mock provider accepted, not inbox receipt; queued/blocked/unknown/cancelled states remain distinct.

## Prepared live protocol, not executed

Owner must approve tenant/account, exact recipient, future slot/window, create/reschedule/cancel/reminder types, cleanup and notification content. Connect tenant-owned OAuth without importing local tokens. Recheck real FreeBusy before each commit; capture event identity/provider readback/dashboard/idempotency. Combine controlled clock semantics with one approved actual reminder email and human receipt. Restore live flags off and cancel only explicitly approved test events/jobs. Never auto-retry uncertain sends or unknown writes.

Separate enrollment/privacy/browser/device approvals remain necessary. No slot or recipient authorization is inferred from this checklist.
