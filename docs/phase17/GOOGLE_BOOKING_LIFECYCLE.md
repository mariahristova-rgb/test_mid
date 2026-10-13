# Calendar lifecycle acceptance

Implementation reused: `concierge.py`, `google_workspace.py`, `tools.py`, widget capability APIs. Policy supports primary plus authorized blocking calendars, Europe/Sofia, weekdays, 30-minute meetings, buffer, configurable year cutoff. FreeBusy and fresh commit checks are present; owned-event reschedule checks exclude only the proven mapped event, not an assumed merged busy interval. Expiring signed management links bind tenant, booking revision and nonce. Google uncertain writes require reconciliation, not blind replay.

Historical approved live evidence: BG create/reschedule/cancel and EN create/cancel on local concierge tenant, October14 test slots, duplicate readbacks and persisted cancellations. EN reschedule and public staging full lifecycle remain unverified. No new Phase17 live event created.

Offline corpus checks availability/DST, explicit confirmation/persistence, signed ownership lifecycle, expiry/revocation and no fake calendar fallback. Test names containing `live` still use mock HTTP transports; they do not certify live integration.

Before live acceptance: owner-approved recipient, exact future slots, action types and cleanup; dedicated staging authorization, operations flag scoped to test tenant, original-event mapping/reconciliation, dashboard/readback and flag-restoration receipts. No original local refresh tokens/database migration.
