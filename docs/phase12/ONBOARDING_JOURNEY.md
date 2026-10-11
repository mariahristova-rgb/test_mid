# Customer journey — 10 October 2026

Use the existing SaaS account screen, Guided setup and Website widgets. They form a linked journey using existing authentication, tenant selection and draft storage. This increment does not add a new identity provider or certify public signup.

1. Sign in. Local demonstration uses `demo / 0000`. Create a fictional organization on Onboarding; select its tenant explicitly. Production uses the configured verified identity provider.
2. Complete email verification and choose the sandbox trial. Local verification email and billing are **MOCK**. No email is sent and no payment is taken.
3. Open Guided setup. Receptionist, Support and Sales provide editable generic instructions. Set business name, website, industry, explicit timezone, BG/EN locales and scheduling policy. Website metadata is not ownership proof.
4. Add approved question/answer pairs in both languages. Turn booking tools off for information-only assistants. Calendars are **MOCK**; slots and confirmed appointments are nevertheless persisted business records.
5. Save, leave and resume a draft. Edits create a new revision and invalidate prior receipts. Run required BG/EN tests: booking, rejection and ambiguity with booking enabled; greeting otherwise; FAQ when configured. Isolated text tests cannot prove speech or live integrations.
6. Explicitly activate the tested Web Chat configuration. This changes tenant-wide business hours/calendar policy; active calls and pending approvals block activation. Use a new fictional tenant for experimentation.
7. Open Website widgets, choose the activated assistant and configure greetings, privacy notice, approved FAQs, exact website origins, color, optional HTTPS logo, retention and quotas. Save creates an unpublished integration.
8. Generate the origin challenge; place its nonce at the displayed well-known path on the authorized website. Verify, then explicitly publish a widget snapshot and copy the generated single script.
9. Install and check launcher, iframe, bootstrap, message, language, keyboard and desktop/mobile behavior separately. Installation remains unverified until these checks pass. Inspect Conversations and Appointments in the selected tenant.
10. Unpublish immediately disables admission and existing capabilities. Rollback selects a compatible immutable snapshot. Revoke permanently disables the public ID; create a new integration to replace it.

The actual HTTP journey used **Fictional Widget Clinic**, tenant `e5de6cb1-6d8d-4726-aa06-a4641bae9b0a`. Eight sandbox cases passed. Two confirmed bookings on 12 October 2026 at 15:00/16:00 Europe/Sofia persisted; duplicate confirmations created no extra appointment. One earlier failed conversation remains visible. Human dashboard review is pending; the owner replied **Not yet checked**.

Remaining UX acceptance: browser-based resume, full installation journey, keyboard/screen reader and mobile checks. The wizard and widget management are linked existing screens, not a single fully validated installation wizard.
