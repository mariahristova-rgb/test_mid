# Billing UX status
Existing billing and exact monetary/usage contracts remain unchanged. No payout system added; no live checkout/card/invoice provider or payment activated. Existing regression covers simulated checkout/webhook/entitlement guards; frontend localization/usage tests and build pass.

Fresh browser billing review is recorded with the regression evidence. Simulation must stay explicitly labelled and separate from real billing. Approved provider configuration, verified signed webhook lifecycle, external invoice/charge/cancellation receipts and human usability acceptance remain BLOCKED. A green synthetic preview never enables payment collection.

Fresh browser finding: the invoice selector displayed the conversation-only placeholder. Replaced only that invoice placeholder with a specific BG/EN paid-test-invoice label; disabled confirmation and mock-only guards remain. Billing page visibly separates simulated accounting/checkout from real payments; no payout or payment action was executed.
