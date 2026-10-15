# Customer journey acceptance
Fresh loopback Phase26C Synthetic Workspace: demo login → New assistant → invalid-name feedback/focus → corrected name/save revision1 → required BG/EN preview tests. This is a browser-observed synthetic journey; no live account consent, payment, external message/event or customer data.

Backend regression covers isolated draft/resume/test/publish gates, FAQ import contracts, permissions, tenant boundaries, provider errors, widget sessions, approval/pending polling and usage precision. Browser observation is not a human nontechnical completion study. Registration/plan/import/provider consent/publish-widget/conversation/usage/disconnect as one complete observed customer journey is NOT_TESTED. Completion time/support-intervention metrics are NOT_MEASURED. Actual external provider connection remains BLOCKED and is not replaced with mocked consent.

Observed result: all six required BG/EN booking/rejection/ambiguity previews PASS for saved revision1. At320/390 widths no visible form controls were clipped; BG locale persisted when navigating to Billing. This does not constitute the complete external customer journey.
