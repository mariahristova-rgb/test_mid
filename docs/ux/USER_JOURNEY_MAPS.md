# Role journeys and evidence

10 October 2026. Before/after describes implemented navigation, not measured clicks or completion time.

| Role | Before | Current flow | Acceptance still needed |
|---|---|---|---|
| Owner | Tenant setup, separate assistant/agent/channel forms, real inbox interaction | Sign in → existing tenant/onboarding → Assistants → Guided setup → save/resume → Test Studio BG/EN → readiness → explicitly activate mock Web Chat | Observed first-run, keyboard and visual review |
| Receptionist | Inbox filters, takeover and reply, separate booking list | Bounded/filterable Inbox → explicit AI paused state → reply/resume → diagnostic metadata → linked appointment/conversation | Attended handover and mobile review |
| Administrator | Long live configuration form and raw activity groups | Assistant sections → isolated draft tests → recorded call/tool outcome → provider capability scope → Advanced settings | Connectivity and real voice acceptance remain separate |
| Demo presenter | Scripts plus calls/appointments reconciliation | Test Studio mock rehearsal → blocked voice warning → inspect existing persisted bookings and scoped call activity | Prior audio/date/consent failures must be resolved before live release |

Failed conversation → diagnostic outcome → suggested synthetic preset in Test Studio → select/review saved draft → rerun. No private conversation is copied. Arbitrary transcript-to-test conversion is not implemented; this safer bounded workflow uses synthetic presets only.

Setup templates change draft instructions, not model or voice providers. Both locales stay mandatory; interface preference is independent of conversation and voice preferences. Business/calendar publishing affects the whole tenant, explicitly warns and confirms, and refuses active calls/pending approvals. Single mock-calendar service is supported; multi-service scheduling is not invented.

No measured time-to-first-success or nontechnical usability result exists. Proposed dry-run: create a synthetic draft, save/leave/resume, run all six required BG/EN tests, explain an ambiguity failure, locate an existing real booking, then inspect channel states. Do not activate a test draft merely to conduct the usability study.
