# Custom integration scoping workflow

Implemented local quote request captures tier, system category, objects, direction, authentication method, environment count and custom-SLA requirement. It never collects passwords, API keys, customer URLs or raw CRM data. Requests persist tenant-scoped with idempotent key/fingerprint and immutable proposed pricing snapshot. Replay with different requirements conflicts.

Status is SCOPING_REQUIRED; commercial_approval=false, subscription_separate=true, simulation=true. Required human reviews: field mapping, security, effort, SLA, acceptance tests, rollback and commercial owner. A simple request cannot claim bidirectional/multiple-environment/custom-SLA work; it requires advanced review instead. Quote request is not a signed offer or invoice.

Simple setup €500–€1,500 + €99/month; Advanced €1,500–€5,000 + €199/month; Enterprise €5,000+ + custom maintenance. Maintenance is separate from SaaS. No charge, payment activation, actual custom adapter, arbitrary HTTP executor or customer code. Implementation/acceptance of a real custom integration requires separately approved provider/security/mapping contracts.
