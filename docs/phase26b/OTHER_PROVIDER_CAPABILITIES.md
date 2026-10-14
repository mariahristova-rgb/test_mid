# Capability-limited provider adapters
| Provider | Implemented local contract | External acceptance |
|---|---|---|
| Google | Signed identity, refresh identity, owner calendar discovery, FreeBusy, durable creation bridge | Not executed |
| Outlook | Signed issuer/audience/nonce identity with explicit tenant allowlist; owned calendar discovery/calendarView, fail closed on pagination/shared calendars | Not executed |
| Calendly | Authenticated users/me identity; event types and scheduled-event reads bound to verified user URI | Not executed |
| HubSpot | Active client-bound introspection, account/scopes binding, CRM read/resource discovery; narrow primitive contact codec | Not executed |

Public customer action grants deliberately expose Google availability/create, Outlook availability, Calendly availability/scheduled_events and HubSpot contact_read. Outlook writes, HubSpot writes/associations and Calendly booking/webhooks are not customer agent workflows. Primitive REST codecs do not imply full lifecycle parity. Calendly plan/role/webhook eligibility remains an external gate; no claim that its current API universally lacks booking support.

References: [Microsoft calendarView](https://learn.microsoft.com/en-us/graph/api/calendar-list-calendarview?view=graph-rest-1.0), [Calendly scopes](https://developer.calendly.com/docs/authentication/scopes), [HubSpot OAuth](https://developers.hubspot.com/docs/api-reference/legacy/authentication/manage-oauth-tokens).
