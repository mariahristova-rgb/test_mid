# Other provider capability evidence
| Provider | Existing local capability | Production acceptance |
| --- | --- | --- |
| Outlook | Fixture Graph discovery, work-account availability and consent-controlled event codec; stale etag tests | Missing actual app/tenant policy and production identity verifier; no live account |
| Calendly | Fixture availability/event-type and scheduled-event reads; signature/replay checks | Hosted/read-only limits preserved; no invented direct-booking API; current app/plan eligibility must be verified before activation |
| HubSpot | Fixture contact lookup/create/update with narrow mappings and duplicate handling | Missing production identity/introspection acceptance and customer app; no deal modifications |

Generic customer lifecycle accepts reviewed provider apps only with an injected verifier. GoogleCustomerIdentity explicitly refuses non-Google providers. Existing fixture success is not parity or live acceptance. No scopes, resources or external accounts were widened.
