"""Write Phase 11 evidence reports from actual local receipts, with explicit gaps."""
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts'
def read(name):
    path=ART/name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
def write(name, text):
    path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text.strip()+'\n',encoding='utf-8')


def main():
    before=read('phase11-api-before-matched.json');after=read('phase11-api-after-matched.json')
    local_before=read('phase11-local-before.json');local_after=read('phase11-local-after.json')
    tests=(ART/'phase11-final-backend.txt').read_text(encoding='utf-8')
    match=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK',tests)
    test_result=f"{match[1]} backend tests passed in {match[2]} seconds" if match else 'Backend completion not verified'
    focused=(ART/'phase11-ux-tests.txt').read_text(encoding='utf-8')
    focused_match=re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK',focused)
    if focused_match: test_result+=f"; latest focused UX suite: {focused_match[1]} tests passed in {focused_match[2]} seconds"
    preserved=bool(local_after and all(local_before.get(key)==local_after.get(key) for key in ('appointment_state_hash','assistant_configuration_hash')))
    deployment='Local API verified; booking and assistant configuration hashes unchanged' if preserved else 'Local deployment verification pending'
    build=(ART/'phase11-frontend-build.txt').read_text(encoding='utf-8')
    chunks=re.findall(r'dist/assets/(\S+\.js)\s+([\d.]+) kB.*?gzip:\s*([\d.]+) kB',build)
    entry=next((float(size),float(gzip)) for name,size,gzip in chunks if name.startswith('index-'))
    total=sum(float(size) for _,size,_ in chunks)
    workspace=next(float(size) for name,size,_ in chunks if name.startswith('WorkspaceView-'))
    css=re.search(r'dist/assets/\S+\.css\s+([\d.]+) kB.*?gzip:\s*([\d.]+) kB',build)
    css_size,css_gzip=map(float,css.groups())
    inventory=subprocess.check_output(['git','ls-files','--modified','--others','--exclude-standard'],cwd=ROOT).decode().splitlines()
    inventory='\n'.join('- `'+name+'`' for name in sorted(set(inventory)))
    header='Checked 10 October 2026. Work restricted to test_mid. Stage 10 was audit/proposal only; the owner explicitly approved the incremental redesign and missing P0 implementation in this phase.'
    write('docs/ux/PHASE11_BASELINE_AUDIT.md',f'''# Phase 11 baseline audit

{header}

Source baseline: 213e0ce on main. Vue 3/Vite/FastAPI/SQLite; the frontend AGENTS.md Next.js guide does not describe the installed Vue application and its referenced Next directory is absent. Existing components/infrastructure are retained.

| Evidence reference | Verified baseline finding | Implemented response |
|---|---|---|
| router/index.ts and App.vue | Fourteen peer links; no skip link or route focus management | Nine primary entries, technical routes in Advanced; skip link and route focus |
| WorkspaceView.load | Ten requests on every workspace route, including unrelated contacts/messages | Route-specific read plans and cancellation of superseded route loads |
| AssistantConfig / voice selects | Asterisk/local STT/TTS omitted; latency input capped below backend range | Complete existing provider enums; 120000 ms contract limit |
| Dashboard badge | WORKING applied to every stored count | Stored-record label; no success-rate interpretation |
| Phase 10 docs and source | No wizard, isolated studio or unified debugger | Draft workflow, disposable simulations, evidence-only diagnostics |
| messaging_api.inbox | Per-conversation message/contact lookups | One SQL enrichment query, tenant-safe filters and 50-row UI pages |
| API benchmark | 1005 read statements for 1000-conversation inbox | Four total request reads including authentication; one inbox statement |
| Phase 9 readiness | Consent/audio/date/human gates unresolved | Explicit blocked voice status; no SIP promotion from mock tests |

Screenshots at desktop/tablet/mobile remain unavailable: existing browser security denied local inspection. No alternate browser, shell capture or indirect UI automation was used. Reproducible references: `/assistants`, `/setup`, `/testing`, `/inbox?conversation=<owned-id>`, `/calls`, `/appointments?conversation=<owned-id>`, `/operations` on local port 3017. Source references are not visual QA.

Baseline click count, task time, actual layout defects, Web Vitals, hydration/render counts and browser memory growth are unknown. There is no verified observed nontechnical dry-run. Existing Phase 8/8B/9 reports remain blocking evidence; three synthetic successful calls were not human-accepted live calls.
''')
    write('docs/ux/COMPETITOR_UX_MATRIX.md',f'''# Competitor UX matrix

{header}

All evidence is official public documentation checked on 10 October 2026, not firsthand authenticated testing. Benefits/effort/risk are design judgments. No screenshots, metrics, branding or layouts are copied.

| Job | Documented pattern / evidence | Current state → response | Benefit / effort / risk |
|---|---|---|---|
| Diagnose a call | [Vapi call logs](https://docs.vapi.ai/observability/logs/call-logs): call artifacts, tools and per-turn stage latency | Grouped activity → metadata timeline and scoped trace panel | Outcome clarity / medium / avoid exposing retained content or equating packets with hearing |
| Test before activation | [Retell simulation](https://docs.retellai.com/test/llm-simulation-testing): scenarios, criteria and function mocks | Developer tests only → BG/EN saved receipts | Repeatability / high / external functions can remain live in that product; our sandbox has no live handles |
| Contextual configuration | [Voiceflow Behaviour](https://www.voiceflow.com/docs/documentation/build/behaviour): model/session/fallback and speech settings; public navigation groups Build/Deploy/Measure | Long forms → read-only sections with draft editing | Progressive disclosure / medium / FAQ is not a document knowledge base |
| Controlled handover | [Fin deployment](https://www.intercom.com/help/en/articles/9356221-deploy-fin-ai-agent-over-email): train/test/deploy, audience and handover | Existing takeover → visible AI pause and preserved controls | Operator confidence / medium / isolated tests are distinct from live delivery |
| Different test scopes | [ElevenLabs testing](https://elevenlabs.io/docs/eleven-agents/customization/agent-testing): simulation, next reply and tool tests | One undifferentiated interaction → explicit mock text scope and blocked audio | Honest coverage / medium / no Bulgarian synthesis inference |

Voiceflow's regression cookbook URL returned an internal fetch error during this phase; its accessible Behaviour page and official index were used. No unavailable page is presented as firsthand evidence. Existing Phase 10 benchmark remains historical research context.
''')
    write('docs/ux/DESIGN_SYSTEM_AUDIT.md','''# Design system audit

10 October 2026. Existing Arial typography, light palette, Vue native controls and CSS remain; no component library or font dependency was added. There was no existing dark-mode implementation, so dark-mode support is not claimed.

Added shared spacing/radius/content/focus tokens, a stronger focus color, skip link, tab-strip styles, wrapping three-panel diagnostics, compact context bar and 44 px control/checkbox-label/link targets. Existing content width is 1400 px; operations collapse at 800 px and diagnostics use single-column mobile panels. Native fieldsets/legends, alerts and status regions are reused. No decorative charts, invented KPIs or loading animations were added.

Source-computed contrast: foreground/background 17.06:1; muted body text/white 7.58:1; links and focus/white 6.70:1; selected tab text/background 5.49:1. These four color pairs are calculations, not a full rendered accessibility audit.

Remaining: actual desktop/tablet/mobile captures, zoom and Cyrillic wrapping verification, complete token migration of older literal values, operational density preferences and screen-reader testing. No claim of visual polish or WCAG conformance is inferred from source.
''')
    write('docs/ux/USER_JOURNEY_MAPS.md','''# Role journeys and evidence

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
''')
    write('docs/ux/ACCESSIBILITY_AUDIT.md','''# Accessibility audit — incomplete acceptance

10 October 2026. Target WCAG 2.2 AA for changed paths; no conformance certification.

Implemented: skip-to-main and route focus; visible 3 px high-contrast focus; native labeled fields and grouped legends; native validation; alert/status regions; reduced-motion override; readable metadata wrapping; checkbox-label and operational-link touch targets; tab roles/selection/panel associations with Left/Right/Home/End keyboard handlers. Mobile debugger selectors are native pressed-state buttons, not fake ARIA tabs. No custom dialog or focus trap was introduced.

Locale tests cover both resources, literal text nodes/keys and changed components, plus scenario/state labels. Contrast calculations for four changed token pairs are in artifacts/phase11-contrast.json. These do not execute keyboard or screen-reader interactions.

UNVERIFIED: desktop/tablet/mobile rendered layout, 200/400% zoom, full contrast inventory, Cyrillic overflow, keyboard-only creation/resume/diagnosis, focus after validation and actual screen-reader announcements. Browser inspection remains blocked. Source lint/unit tests do not replace Playwright/assistive-technology testing; no E2E pass or screenshot count is claimed.

Reproduce manually: tab from sign-in to skip link/navigation, use Assistant Studio arrow/Home/End keys, advance/back/save setup, verify required-field errors, switch BG/EN independently, inspect mobile debugger panels and appointment links. Report focus loss, unlabeled controls or hidden content before marking acceptance complete.
''')
    write('docs/performance/FRONTEND_BASELINE_AND_RESULTS.md',f'''# Frontend baseline and results

10 October 2026; same local host and Vite 8.3.4 production build workflow. Baseline is source 213e0ce. No browser Web Vitals or render profiling could be captured because local browser inspection is blocked.

| Static build measure | Before | After |
|---|---|---|
| Entry JavaScript | 208.83 kB / 67.25 kB gzip | {entry[0]:.2f} kB / {entry[1]:.2f} kB gzip |
| Total emitted JavaScript | 208.83 kB | {total:.2f} kB |
| CSS | 11.88 kB / 3.63 kB gzip | {css_size:.2f} kB / {css_gzip:.2f} kB gzip |
| Routes | Eager Workspace + SaaS | Lazy Workspace, SaaS and Setup |
| Workspace assistant page API plan | Ten reads | Bootstrap + assistants (two reads) |
| Workspace dashboard polling | Calls + appointments + bootstrap | Bootstrap only |

Entry reduction is {208.83-entry[0]:.2f} kB ({(208.83-entry[0])/208.83*100:.2f}% raw), not an overall responsiveness claim. A first dashboard visit also loads Workspace ({workspace:.2f} kB) and shared EmptyState (0.90 kB): raw JavaScript can exceed the old single bundle. Total JS grows with new functionality. A lazy Auth0 experiment generated an extra 216.30 kB SDK chunk and was removed; the existing Auth0 loading behavior is retained.

Commands: npm run lint; npm run typecheck; npm test; npm run build from semantic_os/frontend. Final build output: artifacts/phase11-frontend-build.txt. Route plans are covered by workspace.test.mjs; superseded initial reads are aborted and stale route results discarded. Inbox pages are bounded at 50 rather than loading all conversations. No unmeasured virtualization/memoization or new chart dependency was introduced.

LCP, INP, CLS, p75 field data, route timing, long tasks, browser memory growth, rendered-component counts and visual comparison are UNMEASURED. Aspirational targets remain LCP≤2.5s, INP≤200ms, CLS≤0.1 at p75. Do not infer these from build time or bundle size. Remaining work: authorized browser instrumentation and before/after workloads on the same device; production Auth0 bundle/runtime validation.
''')
    rows=[]
    for key,value in before.get('metrics',{}).items():
        changed=after.get('metrics',{}).get(key,{})
        rows.append('| '+key+' | '+str(value['samples'])+' | '+ ' / '.join(str(value[k]) for k in ('p50_ms','p95_ms','p99_ms'))+' | '+ ' / '.join(str(changed.get(k,'missing')) for k in ('p50_ms','p95_ms','p99_ms'))+' |')
    extras='\n'.join('- '+key+': '+json.dumps(after['metrics'][key]) for key in ('conversation_page','isolated_test_execution') if key in after.get('metrics',{}))
    write('docs/performance/API_DATABASE_BASELINE_AND_RESULTS.md',f'''# API and database benchmark

10 October 2026. Controlled in-process FastAPI/ASGI TestClient, in-memory SQLite, 1000 synthetic conversations, one concurrent request, 40 measured samples per case after warm-up. Before source 213e0ce was exported inside ignored artifacts; matched runs were sequential. No live database/provider was used. Rate-limit budgets are raised only inside this benchmark process. p99 with 40 samples is the maximum nearest-rank sample, not a reliable production-tail estimate.

| Workload | Samples | Before p50 / p95 / p99 ms | After p50 / p95 / p99 ms |
|---|---|---|---|
{chr(10).join(rows)}

{extras}

Full inbox read statements: {before.get('inbox_read_statements')} before, {after.get('inbox_read_statements')} after, including authentication reads. The inbox data itself now uses one SQL statement with tenant-scoped message/contact joins. Legacy unbounded shape and ascending order are preserved; new pages apply filters before cursor/limit. Equal timestamp ties use reception order and mixed timezone offsets compare actual instants. Dates are filtered in the tenant timezone with an exclusive next-day boundary.

Full payload is 207230 bytes versus 10511 bytes for a 50-row page. Smaller pages return less data; this is not an identical full-result workload. Full-list timing did not improve in the matched run, and several earlier runs varied materially. No blanket API speedup is claimed. The direct booking metric excludes HTTP; the HTTP metric covers three message requests and successful confirmation. Conversation detail fixture is empty; call activity fixture has no business execution history.

Query plans are retained in both JSON receipts. Tenant indexes are used; temporary sorting remains. No new index, migration, connection pool, reduced tenant checks or changed ledger rules were introduced. The measured N+1 request pattern justified the query rewrite and bounded paging, not speculative database tuning.

Reproduce: .venv/Scripts/python.exe scripts/benchmark_phase11.py --source-root artifacts/phase11-baseline-source --output artifacts/phase11-api-before-matched.json; then the same command without --source-root to artifacts/phase11-api-after-matched.json. Windows internal loopback sockets require execution outside the restricted sandbox. Initial sandbox runs stalled in asyncio _fallback_socketpair; that is recorded in phase11-backend-diagnostic.txt, not counted as a pass.

No production-network/SQLite-disk/cold-start/concurrent voice API p95 or p99 is established. New call diagnostics share metadata with the existing activity endpoint but lack a separate representative populated-call latency benchmark. Historical operations are process-local aggregates, not stored percentile distributions.
''')
    write('docs/performance/VOICE_DIAGNOSTICS.md','''# Voice diagnostics and resource scope

10 October 2026. Existing Qwen3-4B Q4_K_M, faster-whisper small CPU/int8, BG38/MioCodec, Asterisk/SIP, persistent model volumes and one-call CPU limits remain. No inference image, model, voice, provider credential, recording policy or confirmation mode was switched by the UX work.

Actual idle Docker snapshot before local update: frontend 16.21 MiB (0% CPU), backend 70.11 MiB (0.32%), Asterisk 71.69 MiB (1.88%), TTS 1.343 GiB (0.39%), STT 603.9 MiB (0.34%), Qwen 2.544 GiB (0.01%). These are instantaneous container observations, not peak RAM or capacity guarantees. Host is the previously audited 16 GB Windows/integrated-graphics CPU environment; no CUDA assumption is added. No WSL limit change or duplicate inference service was made.

Debugger exposes only actual content-free voice trace entries: audio/VAD/STT/locale/pending/confirmation/agent/tool/appointment/TTS/first output packet/close where recorded. Trace storage is bounded process memory (256 entries per tenant); restart may remove it. Monotonic times are not wall-clock timestamps. Duration is shown only when measured. Missing and not-applicable coverage are explicit. Metadata may survive while private transcripts remain omitted.

No new SIP booking call, warm/cold model benchmark, audio recording or peak-memory run was performed for Phase 11. Prior failures remain in docs/demo/PHASE9_READINESS.md and PHASE9_SAFETY_PREPARATION.md. Audio sent is not proof of caller hearing, Bulgarian intelligibility, safe consent recognition or PSTN connectivity. Voice acceptance remains DEMO_BLOCKED independently of UX changes.

Next: resolve consent/date speech failures, obtain authorized BG/EN listening and dashboard evidence, then perform the separate attended three-call acceptance. This UX phase cannot waive that gate.
''')
    write('docs/ux/PHASE11_BACKLOG.md','''# Prioritized backlog and status

10 October 2026. Owner approved incremental redesign and missing Phase 10 P0.

| Priority / item | Impact / effort / dependency | Current acceptance |
|---|---|---|
| P0 honest counts/provider scope | High / small / existing metadata | Implemented; no automatic Live Verified state |
| P0 draft/setup/isolated BG/EN testing | High / large / existing orchestration | API regressions pass; resume/revision/side-effect checks present; human journey pending |
| P0 debugger and booking links | High / medium / recorded events | Metadata privacy/ownership/order tests pass; real visual operator review pending |
| P0 keyboard/focus/bilingual barriers | High / medium / Vue native controls | Source and locale coverage pass; assistive-technology/zoom/mobile acceptance pending |
| P1 grouped navigation/Assistant Studio | Medium / medium / owner approval | Implemented progressive/read-only sections and explicit draft entry; visual navigation validation pending |
| P1 inbox performance | High / medium / measured N+1 | Query/payload gains measured; legacy full-list latency not improved |
| P1 frontend delivery | Medium / medium / baseline build | Route splitting measured; total JS grows; Web Vitals unmeasured |
| P1 human takeover | High / small / existing RBAC/control | Preserved with explicit paused state and refreshed selected metadata; observed operator rehearsal pending |
| P2 richer analytics/custom layouts | Unknown / large / instrumentation and usability evidence | Deferred; no fabricated percentiles, unread state, charts or identity merging |

Remaining: observed nontechnical dry-run; browser desktop/tablet/mobile and screen-reader checks; representative call-timeline/production Auth0 timing; real provider connectivity receipts; richer configurable regression scenarios; safe version rollback with business-policy history; multi-service scheduling. Existing tenant registration remains in the SaaS onboarding route. The wizard reuses the tenant's initial assistant rather than duplicating signup infrastructure.
''')
    write('docs/ux/PHASE11_ACCEPTANCE.md',f'''# Phase 11 acceptance — pending human/browser gates

Implemented increment; **Phase 11 is not fully accepted**. UX completion and voice live acceptance are separate, and neither is certified by these reports.

Verified: {test_result}; frontend eleven tests, lint, typecheck and production build passed; source boundary scan reported zero failures. New backend coverage includes BG/EN scenarios, no live side effects, role/tenant boundaries, resume/revision conflicts, stale agent/business/config evidence, confirmation/publish gates, ended/active calls, diagnostic privacy/order, bounded inbox filtering/cursors and timezone ordering. Audio interruption is BLOCKED rather than a fake pass. No browser E2E/visual/a11y interaction result is claimed.

Owner-reported partial review found two real frictions: readiness appeared at step 0 while testing was hidden until step 5; an overlapping owner/automated test produced a generic conflict. Testing is now visible for any saved valid draft, missing evidence says NOT_RUN, worker contention returns localized test_worker_busy, and results/revision recovery actions preserve unsaved edits. All six required cases passed through the actual local API on the owner's saved draft (phase11-owner-draft-tests.json); this was automated API verification, not six observed human completions. One additional passing receipt was observed during the owner interaction. Full save/leave/resume, keyboard and bilingual UI acceptance are still unverified.

{deployment}. Prior live appointment count: {local_before.get('appointment_count','unknown')}; post-update count: {local_after.get('appointment_count','pending')}. Verification does not create a live appointment or activate a draft. No public deployment, repository push, model change or clinic reset was performed by this phase.

Known limits: simulations use deterministic mocks even when the saved draft targets Qwen; mock receipts cannot authorize live-model/SIP/external-message promotion. Wizard activation is limited to tested Web Chat/mock calendar without outbound tools. Publishing explicitly changes tenant-wide business policy and refuses active calls or pending approvals. Shared agents are reused and their changed settings invalidate evidence. Test receipts are bounded (500 per tenant), drafts 50; automatic rollover/deletion is not implemented. Version history covers new workflow activations only; rollback is unsupported. Diagnostics omit transcript bodies and tool arguments.

UNVERIFIED: screenshots, observed usability/click/time results, keyboard/screen-reader/mobile/zoom checks, Core Web Vitals and browser memory, populated-call/production API tail latency. Prior voice consent/date/listening/dashboard gates remain blocked. Full release readiness cannot be claimed.

Reproduction: `.venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests -q`; frontend `npm test`, `npm run lint`, `npm run typecheck`, `npm run build`; `.venv/Scripts/python.exe scripts/check_source.py`; `.venv/Scripts/python.exe scripts/phase11_local_check.py --require-idle --output artifacts/phase11-local-after.json`. Backend TestClient/localhost/Docker commands need permitted Windows socket/pipe access. Local build/update targets only backend/frontend with the existing CPU/neural Compose overlays and --no-deps; original services/volumes remain.

## Changed-file inventory

{inventory}
''')
    ia=ROOT/'docs/ux/INFORMATION_ARCHITECTURE.md'
    previous=ia.read_text(encoding='utf-8').split('\n## Phase 11 implemented navigation')[0]
    ia.write_text(previous+'''
## Phase 11 implemented navigation

Owner-approved incremental redesign, 10 October 2026. Primary: dashboard, assistants, inbox, testing, calls, appointments, operations, integrations, settings. Advanced: setup, agents, channels, onboarding, billing, usage, administration. URLs are preserved; setup/testing are new. Testing/operations require execution-role navigation; administration depends on platform membership. Backend permissions remain authoritative.

Assistants → read-only Overview/Instructions/FAQ when present/Tools/Channels/Voice/Testing/Versions/Activity → explicit draft editing. Setup saves and resumes seven steps. Test Studio reviews synthetic BG/EN outcomes. Calls/Inbox → recorded debugger → linked appointments/conversation. Legacy direct active editing remains visibly Advanced with a warning; it is not presented as draft promotion.

```mermaid
flowchart LR
  A[Assistants] --> D[Saved draft]
  D --> T[Isolated BG / EN tests]
  T --> R[Readiness evidence]
  R --> W[Explicit mock Web Chat activation]
  R --> B[Voice / external activation blocked]
  I[Inbox / Calls] --> X[Recorded diagnostics]
  X --> P[Persisted appointment]
  X --> T
```

Structured breadcrumbs, advanced layout customization and measured navigation usability remain future work. Contextual return links and tenant/environment labels are implemented; a new duplicate signup or tenant identity system is not introduced.
''',encoding='utf-8')


if __name__=='__main__':main()
