# HubSpot contact connector — narrow local scope

Uses authorization preview, OAuth v3 token/introspection codecs and synthetic hub identity. Actions request crm.objects.contacts.read/write only as needed. Discovery exposes selected property names without raw account data. Contact mapping allows email, firstname, lastname and company; all other properties are refused. Writes require consent and an example.invalid email in this fixture-only service.

Email lookup precedes create; an existing contact receives PATCH. Tests prove a second operation key produces one create then one update. This avoids assuming partial email-upsert behavior; concurrent production create/unique-email races still require account-level reconciliation and duplicate-conflict tests. Unknown mutation cannot replay automatically. CRM failure does not mutate any appointment.

[OAuth v3 official guide](https://developers.hubspot.com/docs/api-reference/legacy/authentication/manage-oauth-tokens) and [contact guide](https://developers.hubspot.com/docs/api-reference/legacy/crm/objects/contacts/guide). Contact notes/associations, arbitrary custom fields, legacy ERP, marketplace certification and real customer account consent are not implemented. No claim of unrestricted CRM synchronization.
