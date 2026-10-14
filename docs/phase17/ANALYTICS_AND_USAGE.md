# Analytics and usage boundaries

Reuse `journey.py`, `customer_workspace.py`, immutable usage ledger and strict optional visitor consent. No parallel billing counter or raw transcript analytics added.

Current consented stages include opened/started/availability checked/booking proposed/calendar created/inquiry/human requested, with separate mock/provider scope. They do not provide all impression/bot denominators, slot-selection/verification/reminder/lifecycle completion, cohort conversion or observed SLO series. Report missing values as unavailable, not zero/conversion. Test tenant activity cannot represent production KPI.

Exact measured quantities and reported token/runtime dimensions remain separate from estimated compute costs and provider invoices. No reconciled actual provider cost or hard cloud billing cap is claimed. Phase17 does not add tracking or enable consent by default.
