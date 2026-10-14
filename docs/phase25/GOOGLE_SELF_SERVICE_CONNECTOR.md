# Google Calendar connector — local protocol evidence

The existing owner GoogleWorkspace stays separate and owner-pinned. The new customer-shaped local fixture implements scoped authorization, verified identity, calendar-list decoding and freeBusy/create/PATCH/DELETE codecs. It cannot connect a real customer account or use existing owner tokens.

Action scopes are derived from selected actions; calendar-list readonly supports discovery, freebusy supports availability, events.owned supports mutation. Availability fails closed on missing/error calendar results. Create has deterministic Google-compatible hex event ID; management requires an etag. Writes suppress attendee notifications in the fixture. No email or invite delivery is claimed.

[Calendar list official reference](https://developers.google.com/workspace/calendar/api/v3/reference/calendarList/list) and [web-server OAuth](https://developers.google.com/identity/protocols/oauth2/web-server) inform codecs. Offline tests cover all supported actions in BG/EN and old owner API compatibility. Real calendar permission/resource discovery, customer selection, booking approval bridging and owner-authorized live acceptance remain blocked; no AVAILABLE badge.
