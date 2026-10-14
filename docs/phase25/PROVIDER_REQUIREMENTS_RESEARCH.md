# Provider requirements — initial official-source review

Reviewed 14 October 2026; research only, no provider accounts connected. Feasibility still requires operation-specific scopes, plans and account fixtures before adapter implementation.

| Provider | Verified requirement | Design consequence |
|---|---|---|
| Google | Web-server OAuth exchanges authorization for server tokens; offline access supports refresh | Reuse encrypted server storage and state binding; general self-service must separately replace owner-only assumptions |
| Microsoft Graph v1.0 | getSchedule supports delegated work/school accounts, but not delegated personal Microsoft accounts | Do not advertise uniform Outlook availability; personal/shared calendar strategy needs explicit capability review |
| Calendly | Public multi-user integrations use OAuth; API/webhook access depends on subscription and role | Planned adapter remains COMING SOON until exact scheduling and webhook capabilities are verified |
| HubSpot | Contact API supports record/email lookup; email batch upsert has partial-upsert limitations | Approved field mapping and duplicate handling must respect operation semantics; no generic CRM promises |

Sources: [Google web-server OAuth](https://developers.google.com/identity/protocols/oauth2/web-server), [Graph getSchedule v1.0 permissions](https://learn.microsoft.com/en-us/graph/api/calendar-getschedule?view=graph-rest-1.0), [Calendly API introduction](https://developer.calendly.com/docs/getting-started/introduction), [HubSpot contact API guide](https://developers.hubspot.com/docs/api-reference/legacy/crm/objects/contacts/guide).

Open research gates: Google public consent/verification and calendar resource permissions; Graph create/update/cancel, shared calendars and timezone mapping; Calendly Scheduling API operation limits and signed webhook replay defenses; current HubSpot app platform, OAuth rotation/scopes and association/note permissions. The HubSpot source redirects to a legacy-labelled guide: do not use it alone to choose a new public-app platform. No claim that provider registration or commercial eligibility is complete.
