# Google booking policy and implementation

Initial policy is Monday–Friday, 10:00–19:00 Europe/Sofia, 30-minute duration, 15-minute buffer, 15-minute slot grid and final date 2026-12-31. Duration/buffer/grid/cutoff and reminder settings are configurable; 2027 policy is tested offline. Past/naive/off-grid times and meetings ending after 19:00 are rejected. DST offsets are resolved by ZoneInfo, not the visitor's timezone.

Availability reads Google FreeBusy and fails closed on missing/error calendars. Only available ISO times are returned; no private titles/calendar IDs. Buffers expand occupied periods. The owned primary calendar is checked through Calendar metadata; creation rechecks immediately before insert. Application operations serialize the connected owner account across tenants, with durable intent/fingerprint and deterministic base32-compatible event IDs. Google must confirm the expected ID/private marker/status before a local confirmed appointment is persisted.

The name/email/topic and explicit consent are required; email proof is scoped to the visitor conversation. Optional company is collected. The verified visitor is an attendee. sendUpdates=all supplies Google confirmation/cancellation/update invitations, avoiding duplicate custom confirmation emails. A separate localized email supplies private management access. Meet creation is off unless owner-authorized and metadata supports it; no invented Meet URL is used.

Owner OAuth/real FreeBusy/event tests are NOT RUN. Live operations are off. Offline HTTP contracts do not certify the personal calendar. Google does not offer atomic FreeBusy+insert across other external scheduling applications; our lock protects this application's writes only. External races/in-flight writes require monitoring and reconciliation before production approval. Ambiguous writes are not blindly retried; deterministic IDs permit reconciliation.

Implementation: assistant/google_workspace.py, concierge.py, concierge_api.py and the existing TaskExecutionAgent/ToolRegistry. Legacy mock cancellation/rescheduling is forbidden for Google-backed local rows. No proprietary runtime, paid inference provider or independent bot was added.
