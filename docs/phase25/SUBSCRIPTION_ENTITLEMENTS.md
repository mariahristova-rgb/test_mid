# Connector entitlements

Existing SubscriptionPlan adds optional connector_limit (nonnegative strict integer) and connector_providers (four-provider enum list). Existing plan snapshots lacking these fields preserve compatibility; no default Starter/Growth/Business/Enterprise prices or limits are installed.

PlanEntitlementService.check_connector checks subscription access and provider eligibility server-side. New configurations count all configured fixture connections against the optional cap; disconnect does not evade the cap by recreating records. Idempotent creation returns the previous record without consuming another slot. OAuth/resource/action paths recheck provider eligibility. Recovery list/disconnect remains accessible for authorized owners even after subscription access ends.

No second ledger, invoice, payment gateway or activated offer. Connector limits do not redefine voice/telephony/usage limits. Tests cover forbidden provider, full cap and duplicate create. Proposed custom setup and maintenance are separate from SaaS subscription. Commercial package approval and actual overage billing remain blocked.
