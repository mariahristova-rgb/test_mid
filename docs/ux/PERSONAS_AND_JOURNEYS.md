# Personas and journeys — proposed

10 October 2026. These are design hypotheses; no observed nontechnical dry-run, measured click counts or completion timings exist.

| Persona | First run | Daily operation | Troubleshooting |
|---|---|---|---|
| Clinic manager | Sign in/select tenant, Receptionist template, business/hours/timezone/services, BG/EN, permissions, isolated test, readiness | Review confirmed appointments and outstanding conversations | Read failed scenario outcome and next action, ask administrator for provider failures |
| Receptionist | Open assigned inbox; see channel, language and AI state | Navigate conversation ↔ booking; explicit takeover/reply/resume | Distinguish pending proposal from persisted appointment and failed delivery |
| Administrator | Configure provider connection separately; verify tenant permissions | Check provider evidence and usage scope | Inspect correlation, recorded stages and missing diagnostics; never raw keys or model reasoning |

Primary proposed demo: demo sign in → existing/create authorized tenant → template → business → languages/voice → two agents/tools → channels → BG and EN isolated simulations → readiness review → explicit SIP activation only when gates pass → attended booking call → real appointment/conversation inspection → separately confirmed safe reset. Voice activation remains blocked by Phase 9; simulation success cannot unlock it.

Failure recovery: saved setup resumes at last valid step; unavailable slot leaves no booking; ambiguous confirmation remains pending; lack of trace says Not recorded; unauthorized actions explain role requirement without exposing another tenant. Reset is maintenance, not a wizard completion action.

Validation protocol after P0: ask an available nontechnical tester to configure a synthetic clinic, run BG/EN tests, explain a failed booking, locate a real prior booking and identify channel statuses. Record consent, task start/end, navigation actions, errors and assistance. Report observed results only; do not substitute developer assertions for usability evidence.
