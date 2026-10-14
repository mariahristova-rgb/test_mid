# Approved first no-code increment

13October2026. Owner explicitly approved optional Business fields/mock schedule/BG-EN UI/fixture tests. Implemented in ux.py,calendar.py,SetupView.vue,locales and businessSchedule helper. No DDL,external activation or new customer database.

New fields: description≤1000,contact_email≤250(valid mailbox),contact_phone≤50(unverified metadata),service_price optional exact decimal string≤9integer/2fraction digits,EUR/BGN/USD currency,≤100unique ISO closed dates and≤100increasing aware unavailable intervals. Decimal comma is normalized; no money is collected or added to billing. Business profile is persisted through existing draft→explicit test/publish→tenant JSON workflow. Description/contact/price are stored metadata, not automatically certified FAQ/LLM grounding.

UI uses date and datetime-local controls in explicit business timezone; helper resolves aware UTC values independently of browser timezone and refuses invalid/ambiguous/nonexistent DST times. Legacy drafts receive optional defaults on edit; original config/receipt hashes are not rewritten until save. Concurrent business profile changes invalidate new drafts; legacy base hashes remain supported. Existing tenant-wide effects/activation warnings preserved.

Mock calendar checks local closed dates and overlapping intervals for availability/create/reschedule; isolated TestStudio simulation projects the same rules. Google Calendar policy remains separately approved; the UI states this scope. Tests assert draft resume,validation,serialization,explicit publication,other tenant unchanged,closed/block/boundary availability and no real appointment/channel activation. The fixed TestStudio booking sample may correctly fail when its date is configured closed; this is not a passing booking receipt.

Verification: setup targeted22PASS/3.221s before final concurrent-profile test; full351backendPASS/47.365s; frontend37PASS/typecheck/lint/build; corpus1.3.0 41/41PASS; schema1–5/integrity/FKs/data preservationPASS; source242/0failures. Initial Vue newline warnings fixed; initial barge-in fixture used listening rather than speaking and was corrected without voice runtime changes.

No live browser/UI-owner rehearsal performed; API/compile/helper evidence is synthetic, not proof a human completed the screen. Catalogue/multi-service prices,cancellation rules,arbitrary business-owner OAuth and productionvoice activation remain incomplete. Current increment does not complete allPhase21requirements.
