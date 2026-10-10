# Demo release checklist

**DEMO_BLOCKED — preparation only.** Phase 8B has not passed the mandatory human/speech acceptance gate. No release candidate is certified and no new Phase 9 live rehearsal, reset, public release or real notification was performed.

Verification date: 2026-10-09T11:32:44.587587+00:00. VERIFIED applies only to the named evidence scope. PREPARED/NOT_CONFIGURED are checklist states, not successful live acceptance.

| Item | Status | Evidence | Last verified | Responsible component | Remaining action |
|---|---|---|---|---|---|
| Application build | VERIFIED | fresh frontend-build.txt | 2026-10-09 | frontend | No live UI certification |
| Backend tests | VERIFIED | 222 backend tests passed in 48.999 seconds | 2026-10-09 | backend QA | Rerun after any further code change |
| Frontend tests | VERIFIED | 9 fresh tests/lint/typecheck/build | 2026-10-09 | frontend QA | Human visual evidence remains |
| Docker health | HEALTHY | readiness.json component probes | 2026-10-09 | demo operations | No whole-workflow inference from health |
| SIP registration | BLOCKED | historical Phase 8B registered calls only | 2026-10-09 | telephony | New attended rehearsal after gate |
| Qwen inference | HEALTHY | loaded worker + historical probes | 2026-10-09 | inference | New fixed-date performance rehearsal |
| Bulgarian STT | BLOCKED | question false consent in stt-matrix.json | 2026-10-09 | speech | Correct and validate acoustic safety |
| Bulgarian TTS | BLOCKED | actual WAV/RTP, listening pending | 2026-10-09 | speech/owner | Human intelligibility/date/name review |
| English STT/TTS | BLOCKED | historical EN business success; listening pending | 2026-10-09 | speech/owner | Complete attended acceptance |
| Agents/tools/tenant | VERIFIED | readiness + fresh regression suite | 2026-10-09 | backend | Live scoped dashboard action verification |
| Booking persistence | VERIFIED | historical 3 IDs/restart + fresh deterministic tests | 2026-10-09 | backend | Fresh release rehearsal |
| Dashboard visibility | BLOCKED | HTTP 200, owner visual check pending | 2026-10-09 | frontend/owner | Inspect actual call/conversation/agent/tool/appointment |
| Demo seed | VERIFIED | idempotent marked tenant; two dentists/templates | 2026-10-09 | demo operations | Do not duplicate or change original seed date |
| Demo reset | BLOCKED | disposable repeat/scope/active-call tests pass | 2026-10-09 | demo operations/owner | Explicitly confirmed operational rehearsal; not run live |
| Presenter scripts | PREPARED | BG/EN scripts + fixed demo-plan.json | 2026-10-09 | presenter | Rehearse numeric date speech and 8–12 min timing |
| Fallback | PREPARED | existing bilingual Web Chat; isolated mock artifact | 2026-10-09 | presenter | Label fallback/recorded evidence honestly |
| Notifications | NOT_CONFIGURED | no live tenant connections; templates/offline mock fixture | 2026-10-09 | messaging | Simulated preview only; no external send |
| Release source | BLOCKED | Git commit/RC ID null; documented untracked source | 2026-10-09 | repository owner | Review and freeze source only after gate passes |

No mandatory failed item can be converted to DEMO_READY_WITH_LIMITATIONS. The actual runtime, test, inventory and acceptance evidence is under artifacts/phase9; historical live evidence remains distinctly under artifacts/phase8b.
