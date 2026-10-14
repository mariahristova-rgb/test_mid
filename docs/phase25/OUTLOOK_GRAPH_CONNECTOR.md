# Outlook Graph connector — local protocol evidence

Uses Graph v1.0 codecs, Microsoft authorization-code preview with PKCE, offline_access and User.Read. Calendar discovery projects IDs/canEdit. ReadBasic is requested for availability; ReadWrite for mutations. Events carry explicit UTC dateTimeTimeZone converted from aware inputs; deterministic transactionId and management If-Match are tested. No attendee list is sent.

getSchedule supports work/school delegated accounts, not personal delegated accounts. Personal/shared availability requests therefore fail closed here. Shared-calendar rights and a personal-account calendarView strategy remain unsupported rather than silently assumed. See [getSchedule permissions](https://learn.microsoft.com/en-us/graph/api/calendar-getschedule?view=graph-rest-1.0), [event create](https://learn.microsoft.com/en-us/graph/api/user-post-events?view=graph-rest-1.0) and [authorization flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow).

Offline requests verify UTC conversion, transactionId, consent, stale etag and unknown-write refusal. No Entra app registration, admin consent, real mailbox access or invitations. Public availability remains COMING_SOON; shared/personal account support is an explicit open capability gate.
