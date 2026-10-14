# UX and billing acceptance
Existing Vue five-stage setup, ordered BG/EN profile saves, draft revisions, mock-only testing/publish gates, explicit cancellation and mock-payment isolation are preserved. No new broad redesign or merchant payout feature introduced.

Phase26A browser evidence: setup/Billing 320/390/768/1280 widths without page overflow, visible buttons >=44px and no underline; Save/Continue and profile locale reconciliation observed. Corrected invalid-input focus/atomic alert present. Human screen-reader still FAIL. Owner waived involvement for local continuation only; no accessibility PASS invented.

Customer connection UI integration and complete register → import → OAuth → BG/EN booking → widget publish → usage → disconnect journey remain pending. Real OAuth consent cannot be silently simulated. No billing/payment action submitted. Existing frontend/source contracts must pass after any new UI increment.
