# Provider boundaries — official documentation reviewed 15 October 2026
| Provider | SUPPORTED local implementation | MOCK_ONLY evidence | BLOCKED / UNSUPPORTED |
|---|---|---|---|
| Google | Tenant OAuth, owned resource, availability, durable creation | Provider contracts; PostgreSQL booking runtime | Real-account/remote receipt BLOCKED; customer reschedule/cancel UNSUPPORTED |
| Outlook | Tenant-allowlisted signed identity, owned calendarView, read scopes | Identity/refresh/resource/pagination contracts | Account consent BLOCKED; shared calendars, writes, delta/subscriptions UNSUPPORTED |
| Calendly | Verified user URI, event types/availability/scheduled-event reads | Account/resource codecs and authorization contracts | Real plan/role eligibility BLOCKED; webhooks, hosted-link UX and direct booking/reschedule/cancel UNSUPPORTED |
| HubSpot | Active client-bound identity; contact-read public capability | Narrow contact read/write codecs only | Actual CRM receipt BLOCKED; customer write/dedup/associations/notes workflow UNSUPPORTED |

Server catalog action allowlist and BG/EN UI expose only implemented grants. Missing app/tenant policy disables connection. REST codecs do not establish parity. Existing negative tests cover scope changes, wrong account/resource, timeout/rate limits, revocation and tenant access. Customer Calendly webhooks are not registered, so no signature/replay/order acceptance is claimed; unsupported operations stay disabled.

Outlook: Calendars.ReadBasic works for delegated personal/work calendar reads, but actual implementation requires a preapproved identity tenant and rejects shared resources; personal account tenant policy is not universally enabled. CalendarView expands recurring instances; live recurrence/delta/subscription acceptance remains absent. [Graph permissions](https://learn.microsoft.com/en-us/graph/permissions-reference).

Calendly officially has a Scheduling API; plan/role restrictions must be verified per endpoint/account. Its FAQ and overview describe different eligibility scopes; no inferred Free-plan booking entitlement. Reschedule can emit both created/canceled notifications, but this application does not consume those customer webhooks. [FAQ](https://developer.calendly.com/docs/getting-started/frequently-asked-questions), [overview](https://developer.calendly.com/api-docs/overview), [reschedule notifications](https://developer.calendly.com/docs/api-guides/trigger-automations-with-other-apps-when-invitees-schedule-or-cancel-events).

HubSpot supports contact operations, but email/external-ID dedup, uncertain writes and consent must be implemented as a workflow before enabling writes. No deal modifications. [Contacts documentation](https://developers.hubspot.com/docs/api-reference/legacy/crm/objects/contacts/guide).
