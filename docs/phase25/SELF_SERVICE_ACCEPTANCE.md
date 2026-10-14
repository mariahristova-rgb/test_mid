# Self-service acceptance — local versus external

14 October 2026. Existing `test_connectors.py`, Google/booking tests and versioned corpus are used; no parallel acceptance framework. PASS below is offline evidence, not vendor certification or a real appointment.

| Scenario | Result / evidence |
|---|---|
| 1 Catalog Google | PASS BG/EN compiled render and browser; owner-only versus planned separation |
| 2 Simulated OAuth | PASS four providers; authenticated private fixture completion |
| 3 Calendar discovery | PASS Google/Graph response codecs; synthetic resources only |
| 4 Action selection | PASS server provider/action/resource allowlists; UI checkboxes |
| 5 Booking | PASS Google/Graph create codecs; existing assistant booking suite retained; new connector does not book application appointments |
| 6 Scopes | PASS missing-grant refusal and action-derived scopes |
| 7 Expired token | PASS serialized rotated token fixture and reauthorization handling |
| 8 Revocation | PASS local disconnect clears fake material; remote revoke NOT TESTED |
| 9 Tenant isolation | PASS cross-tenant rows/state/role refusal |
| 10 Outlook | PASS work-account availability/create/management codecs |
| 11 Shared calendar | Safe unsupported refusal; real shared/personal support NOT IMPLEMENTED |
| 12 Calendly plan | Read-only bounded scope; real plan/role entitlement NOT TESTED |
| 13 Webhook replay | PASS signed internal fixture, tolerance and receipt deduplication; no public webhook |
| 14 HubSpot duplicates | PASS email lookup followed by one create then PATCH on second key |
| 15 CRM failure | PASS provider failure/uncertainty isolation; no appointment changes |
| 16 Subscription cap | PASS configured count/provider gate; legacy plans remain compatible |
| 17 ERP quote | PASS scoping request, pricing snapshot, no commercial approval/payment |
| 18 Unknown writes | PASS persisted pending/unknown receipt, no automatic retry/reconnect |
| 19 Legacy configurations | PASS existing owner Google API and full-suite/schema regressions |
| 20 No secrets/external effects | PASS encrypted fake tokens/redacted projection; real transport refused; zero appointment/job/invoice writes |

Browser: existing named Phase24 Synthetic Workspace was explicitly refreshed as a disposable in-memory fixture, loopback 8019. Four EN OAuth cards connected; Google/Outlook/Calendly availability and HubSpot contact-write preview passed, repeated in BG. EN simple and BG advanced scoping requests remained pending commercial review. No vendor URL opened or owner configuration/activation submitted. Actual 320px client/scroll widths both 305px; 11 visible input/select controls had associated labels. Keyboard ArrowDown selected quote tier and Enter submitted. This is sampled interaction, not complete keyboard-only navigation or screen-reader certification. Viewport reset. Screenshot: ignored `artifacts/phase25/provider-workspace.jpg`.

Recovery/production/shared-account/vendor webhook gates are intentionally unresolved; no Phase 25 public SaaS GO. User-attested Phase 24 accessibility does not certify the new connector forms.
