"""Prepare blocked-demo operational documents from actual audit/test evidence."""
from datetime import datetime, timezone
import hashlib
import argparse
import json
from pathlib import Path
import re
from textwrap import dedent

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/demo'
EVIDENCE=ROOT/'artifacts/phase9'


def write(name,text):
    (OUT/name).write_text(dedent(text).strip()+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--audit',type=Path,default=EVIDENCE/'readiness.json')
    parser.add_argument('--tests',type=Path,default=EVIDENCE/'backend-tests.txt')
    args=parser.parse_args()
    readiness=json.loads(args.audit.read_text(encoding='utf-8'))
    inventory=json.loads((EVIDENCE/'version-inventory.json').read_text(encoding='utf-8'))
    tests=args.tests.read_text(encoding='utf-8')
    match=re.search(r'Ran (\d+) tests in ([\d.]+)s',tests)
    if not match or not tests.rstrip().endswith('OK'):raise RuntimeError('Fresh backend regression report required')
    observed=f"{match[1]} backend tests passed in {match[2]} seconds"
    verified=readiness['verified_at']
    inventory['git_commit']=readiness.get('git_commit')
    inventory['git_state']='local preparation checkpoint; release-source freeze pending' if inventory['git_commit'] else 'uncommitted source'
    source_description=(f"Local preparation checkpoint: {inventory['git_commit']}. Subsequent source changes must be reviewed/committed before freezing an RC. No release tag or remote push was created." if inventory['git_commit'] else 'Git has no commit and Git-visible source/config/docs are untracked; no committed release candidate exists.')
    blocked='**DEMO_BLOCKED — preparation only.** Phase 8B has not passed the mandatory human/speech acceptance gate. No release candidate is certified and no new Phase 9 live rehearsal, reset, public release or real notification was performed.'
    blockers='\n'.join('- '+b for b in readiness['blockers'])
    image_table='| Service | Running image ID | Runtime state |\n|---|---|---|\n'+'\n'.join(f"| {r['component'].removeprefix('docker_')} | {r['evidence']['image_id']} | {r['status']} |" for r in readiness['components'] if r['component'].startswith('docker_'))
    inventory['database_migration_version']=next(r['evidence']['migration_version'] for r in readiness['components'] if r['component']=='database')
    inventory['running_docker_images']={r['component'].removeprefix('docker_'):r['evidence'] for r in readiness['components'] if r['component'].startswith('docker_')}
    inventory['dependency_configuration_hashes']={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'semantic_os/backend/requirements.lock',ROOT/'semantic_os/backend/requirements-stt.lock',ROOT/'semantic_os/frontend/package-lock.json',ROOT/'semantic_os/deploy/compose.cpu-voice.yml',ROOT/'semantic_os/deploy/compose.cpu-neural.yml',OUT/'demo-plan.json']}
    (EVIDENCE/'version-inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
    write('PHASE9_READINESS.md',f'''# Phase 9 readiness decision

{blocked}

Audit: {verified}. All seven prerequisite reports were inspected; latest actual Phase 8B per-call receipts and acoustic controls were checked rather than treating the prior summary as approval.

## Exact blockers

{blockers}

Three selected-affirmative synthetic SIP business workflows passed in Phase 8B with distinct appointments and restart persistence. They are not three human-accepted calls. The owner reported an initial dashboard connection refusal; the intended port 3011 returned HTTP 200, but actual visual rows remain unverified. The Ivan telephone-band question control became affirmative in all three decode variants. These are mandatory failures; DEMO_READY_WITH_LIMITATIONS cannot waive them.

## Isolated preparation completed

Read-only readiness command, version inventory, fixed dated presentation plan, safe reset confirmation/seed preservation, disposable reset/idempotency/isolation tests, bilingual presenter scripts, customer-journey/recovery/checklist documents. Existing bounded two-second UI polling is retained; no dashboard redesign or new live event simulation was added. Bilingual templates are present; current tenant Email/SMS/WhatsApp connections are NOT_CONFIGURED. Four existing offline mock messaging scenarios were reproduced independently, not delivered or inserted into the live dashboard.

Fresh verification: {observed}. Frontend nine tests, lint, typecheck and build were rerun and passed. Source/secret checks are recorded in artifacts/phase9/final-checks.json when complete. No proprietary semantic runtime or paid voice provider was introduced. Backend reset safeguards are source changes for offline maintenance; they were not deployed to or exercised against the running database.

## Reproducibility inventory, not a release

{source_description} Frontend's existing application version is 0.1.0; no independent backend release version is declared. RC identifier remains null while the mandatory gates are blocked.

Qwen: {inventory['qwen']['source_revision']}, Q4_K_M, SHA-256 {inventory['qwen']['quantized_sha256']}. Original BF16 assets are untouched. STT: {inventory['stt']['version']}. TTS: BG38 {inventory['tts_models'][1][1]} and MioCodec {inventory['tts_models'][0][1]}; Windows Ivan remains evaluation-only. Migration version: {inventory['database_migration_version']}.

{image_table}

Pinned image references/model revisions and dependency/configuration hashes are captured in artifacts/phase9/version-inventory.json. Runtime image IDs are existing local images, not newly published immutable release artifacts. Python constraints, frontend lockfile and both Compose files are retained. This audit does not rehash all model weights; existing verified startup caches are preserved.

## Required next gate

Resolve the acoustic consent control failure, obtain genuine BG/EN listening and visual dashboard evidence, then repeat three consecutive complete SIP journeys. Only then freeze a reviewed source commit/configuration, build a dedicated RC, rehearse fixed dates/reset/restart and decide release readiness. Public-network calling, real clinic calendars, real notifications/payments, production identity/security/recovery/capacity remain separate unverified integrations.
''')
    write('DEMO_HEALTH_CHECK.md',r'''# Read-only demo health command

Run from test_mid:

```powershell
powershell.exe -NoProfile -File scripts/demo/readiness.ps1
```

Python equivalent: `.venv/Scripts/python.exe scripts/demo_readiness.py`. Report: artifacts/phase9/readiness.json. Python/PowerShell wrapper return 2 when blocked; a parent shell may represent a failing native command differently. Read the explicit JSON decision, not just a shell success icon.

RUNNING means an owned process exists. HEALTHY means an actual health/HTTP/configuration probe passed. VERIFIED is limited to the stated database/tenant/configuration/fixed-slot check. BLOCKED means missing/failed evidence with a remaining action. None alone proves caller-heard speech or visible dashboard bookings.

Checks: six project-owned containers/image IDs; Asterisk PJSIP endpoint 1001; Qwen model health; existing STT/TTS health; ARI gateway; backend API; read-only SQLite integrity/foreign keys/migration 5; marked SmileCare tenant/two dentists; both agents/booking tools; voice/Web Chat and one concurrent session; HTTP dashboard; fixed future slots through the existing mock calendar and authoritative appointment reads. It reads Phase 8B receipts and fails closed on missing human/UI/acoustic evidence or duplicate booking IDs.

No call, reservation, reset, model download, inference-worker duplication or external send occurs. It never serializes environment variables/secret values. Qwen/STT/TTS process health does not replace actual inference/pronunciation tests. SIP endpoint presence establishes configuration capability, not new registration or PSTN access. HTTP 200 is not visual UI verification.

The blocked audit is intentional. See PHASE9_READINESS.md and DEMO_TROUBLESHOOTING.md. Do not change a result field to remove a blocker; obtain and retain new real evidence after correcting the underlying problem.
''')
    write('DEMO_RESET.md',r'''# Demo reset and repeatability

DEMO_BLOCKED. Preparation changes were tested only on disposable stores. The live tenant and all Phase 8B booking/audit evidence were preserved; no Phase 9 operational reset was performed.

The marked tenant is smilecare-demo, marker testmid-smilecare-synthetic-v1. Reset rejects other/unmarked tenants, production mode and active calls. It archives demo-created confirmed appointments, pending approvals/jobs and closes demonstration conversations. Required seeded_fixture appointments remain confirmed. It keeps assistants, both dentists, templates, seed customers and execution/audit/usage records. Repeated reset creates no new tenants or appointments; seeding an existing marked tenant does not duplicate data.

Before an owner-authorized reset: save the acceptance artifacts, verify zero active calls, and stop only the dedicated demo writer/services. Never invoke host SQLite maintenance concurrently with Docker's writer.

```powershell
powershell.exe -NoProfile -File scripts/demo/stop-local.ps1
powershell.exe -NoProfile -File scripts/demo/reset-demo.ps1 -Confirm
powershell.exe -NoProfile -File scripts/demo/start-local.ps1 -NeuralVoice
powershell.exe -NoProfile -File scripts/demo/readiness.ps1
```

The wrapper requires -Confirm before any maintenance and checks scoped services are stopped. Direct CLI requires --confirm and a dedicated .assistant-data database. Prefer the wrapper; the direct CLI does not prove every possible separately launched writer is stopped. Do not run these destructive/archival steps merely to obtain a green report. No database deletion or volume removal is required.

The runtime's available slots are computed from seeded weekday/resource policy; they are not pre-booked placeholder appointments. The fixed demo-plan.json date must still be future and free. Existing historical seed fixtures retain their original date; reset does not silently move dates. After a permitted reset/restart, verify two seed fixtures remain, old demo-created appointments are cancelled, conversations are closed, audit retained and no duplicate seed was created. Live reset/restart rehearsal remains NOT_PERFORMED until Phase 8B passes.
''')
    write('DEMO_CUSTOMER_JOURNEY.md',f'''# Planned customer journey

{blocked}

Versioned fixed plan: demo-plan.json, **13 October 2026**, Europe/Sofia, 30 minutes. Planned BG 15:00, EN 16:00 and repeat BG 17:00 are currently future/free for both fictional dentists under the existing seeded mock policy. Read-only audit created no reservation. This fixed-date voice rehearsal has not been performed; supported text forms are numeric/ISO and speech may not preserve them. Stop on a mismatched proposal rather than substituting “tomorrow” or guessing.

| Step | Existing implementation/evidence | Required live verification |
|---|---|---|
| Dial | Authorized loopback SIP endpoint 1001 dials extension 2000; Asterisk/ARI resolves SmileCare/default | New attended registration/routing/audio; no public carrier claim |
| Greeting | Seeded BG/EN SmileCare greetings; existing BG38 response provider | Intelligible first greeting, active voice locale |
| Request | Receptionist, locale/state, missing date/name collection | Unambiguous fixed date/time and verbatim synthetic name |
| Handoff | Existing tenant/assistant/conversation/call/locale/intent/arguments/correlation handoff | Actual scoped execution details, no fabricated event stream |
| Availability | Existing mock calendar, Mon–Fri 09–18, two dentists/30 minutes | Free slot and unavailable branch; clearly say demo calendar |
| Confirmation | Phase 8B exact pending-context decision and permission checks | Reject questions/negatives/ambiguity; question ASR control remains failed |
| Persist | Transactional approval/tool/calendar path, one-per-call idempotency | Correct persisted ID and replay does not create another |
| Speak | Local TTS after business result; RTP output packets | Human hears correct name/date/time in active language |
| Dashboard | /dashboard, /assistants, /inbox, /calls, /appointments; call activity shows agents/tools | Human sees actual rows/status/timestamps; metadata-only voice history reflects privacy settings |
| Notification | Bilingual templates, offline mock scenario artifact | No live provider; only explicitly simulated preview, not delivered message |
| Reset/repeat | Confirmed demo-only archival maintenance, seed preservation | Owner-approved operational rehearsal after gate passes |

UI locale, conversation locale and voice locale are separate. An English UI preference must not change a Bulgarian call. No transcript storage or audio recording is enabled automatically to improve the demonstration; real caller retention needs the configured lawful basis/consent. Existing UI polling is bounded to two seconds, skips busy/overlapping work and reports errors; visual responsiveness remains unverified.
''')
    write('PRESENTER_SCRIPT_BG.md','''# Сценарий за представяне — подготовка, 8–12 минути

**DEMO_BLOCKED. Не представяйте този план като одобрена жива демонстрация.** Първо са необходими безопасно разпознаване на потвърждението, прослушване и проверка на таблото. Фиксирана дата: 13.10.2026, Europe/Sofia; ако е минала, спрете и подгответе нов версиониран план.

1. 0–1 мин: „Това е самостоятелен AI асистент с български и английски език. Показваме измислена клиника SmileCare и демонстрационен календар.“
2. 1–2 мин: Отворете /dashboard и /assistants на http://127.0.0.1:3011. Покажете локалния Qwen3-4B, Receptionist и Task Execution Agent. „Първият агент разговаря с клиента; вторият изпълнява разрешени действия.“
3. 2–5 мин: След преминаване на приемателния gate, разрешеният SIP клиент набира 2000. Очакван поздрав: „Здравейте! Свързахте се със SmileCare. Как мога да Ви помогна?“ Кажете точно: „Искам да запиша час за 13.10.2026 в 15:00.“ После: „Казвам се Мария Демо.“ Проверете изговорените име, дата, час и 30 минути. Само ако са правилни: „Да.“ При грешка не потвърждавайте. Няма право да се заобикаля неясна реч или да се измисля успешен резултат.
4. 5–7 мин: Покажете действителния booking ID, /appointments, /calls и call activity: двата агента, CheckAvailability и CreateAppointment. Не представяйте нередактиран разговор, ако съхранението на транскрипт е изключено.
5. 7–10 мин: Английският SIP сценарий използва точната фраза „I would like to book an appointment for 2026-10-13 at 16:00.“ После „My name is Jane Example.“ и, само след правилно предложение, „Yes, confirm.“ Това е планиран, все още нерепетиран абсолютен гласов формат.
6. 10–12 мин: „Използваме локална SIP връзка, не доказана публична телефонна мрежа. Календарът и известията са демонстрационни. Не заявяваме производствена готовност.“ Известията се показват само като ясно означена симулация; реални съобщения не се изпращат.

Не скривайте измерените десетки секунди изчакване. Ако общото време надхвърли 12 минути, прекратете второто обаждане безопасно и обяснете ограничението. Отделната приемателна репетиция изисква три последователни напълно проверени разговора; третият български е планиран за 17:00 с „Иван Пример“.

Резервен вариант: обозначен Web Chat със същите агенти и цифровата фиксирана дата. Кажете „Това е Web Chat, а не успешно телефонно обаждане.“ Показването на историческите Phase 8B записи трябва да е означено като запис, не като жив резултат. Reset се изпълнява само след изрично -Confirm и спряна демонстрация.
''')
    write('PRESENTER_SCRIPT_EN.md','''# Presenter script — preparation, 8–12 minutes

**DEMO_BLOCKED. This is a planned script, not an accepted live demonstration.** First resolve safe speech consent and obtain listening/dashboard evidence. Fixed date: 13 October 2026, Europe/Sofia. Stop and version a new plan if the date expires.

1. 0–1 min: “This is a self-hosted AI Assistant supporting Bulgarian and English. SmileCare is fictional and the calendar is a demo calendar.”
2. 1–2 min: Open /dashboard and /assistants at http://127.0.0.1:3011. Show local Qwen3-4B, Receptionist and Task Execution Agent. “The receptionist talks to the customer; the execution agent performs authorized actions.”
3. 2–5 min, after the acceptance gate passes: authorized SIP client dials 2000. Expected configured greeting: “Hello! You have reached SmileCare. How can I help you?” Say exactly: “I would like to book an appointment for 2026-10-13 at 16:00.” Then “My name is Jane Example.” Verify the proposed name, fixed date, time and 30 minutes. Only then say “Yes, confirm.” Stop on a wrong or unclear proposal. This absolute spoken date format is planned, not rehearsed.
4. 5–7 min: Show the actual persisted booking ID, /appointments, /calls and selected call activity. Show both agents, CheckAvailability and CreateAppointment. Explain metadata-only voice history when transcript retention is disabled; never fabricate conversation text.
5. 7–10 min: Bulgarian scenario uses “Искам да запиша час за 13.10.2026 в 15:00.” Then “Казвам се Мария Демо.” and, only after a correct proposal, “Да.” The expected greeting is “Здравейте! Свързахте се със SmileCare. Как мога да Ви помогна?” Verify the dashboard language preference does not change the caller locale.
6. 10–12 min: “This demonstrates local SIP, not verified public-network telephony. The clinic calendar and notifications remain mocked. This is not production certification.” Show notification templates/isolated simulated output only as simulated; no real send is authorized.

Do not conceal measured long stage delays with a fabricated success message. If the script exceeds 12 minutes, safely stop the second call and disclose latency. The separate acceptance rehearsal needs three consecutive fully accepted calls; repeat Bulgarian at 17:00 for Иван Пример.

Fallback: explicitly labeled Web Chat using the same agents and fixed numeric date. Say “This is the Web Chat fallback; it is not a successful live voice call.” Existing Phase 8B recordings are historical recorded evidence, not new live events. Reset requires explicit -Confirm after stopping only this demo.
''')
    write('DEMO_TROUBLESHOOTING.md',r'''# Scoped failure recovery

DEMO_BLOCKED. Preserve failures/evidence; do not replay an uncertain booking action. Confirm active calls are ended before restarting a service. Do not stop unrelated cruise containers or rebuild the entire stack for a minor issue.

Base commands from test_mid:

```powershell
docker compose -p testmid-cpu-voice --env-file artifacts/local-demo/compose.env -f semantic_os/deploy/compose.cpu-voice.yml -f semantic_os/deploy/compose.cpu-neural.yml ps
docker compose -p testmid-cpu-voice --env-file artifacts/local-demo/compose.env -f semantic_os/deploy/compose.cpu-voice.yml -f semantic_os/deploy/compose.cpu-neural.yml logs --tail 80 backend
```

Use the same flags and substitute only the affected service for logs or `restart`. Never dump Compose configuration, environment variables, SIP auth files or secret values. Inspect/redact any operational logs before sharing them. Scripts/demo/readiness.ps1 is the single read-only audit.

| Failure | Diagnostic evidence | Safe next action |
|---|---|---|
| Asterisk stopped | owned container status, scoped Asterisk logs | Start existing Asterisk image; verify endpoint 1001 and ARI app |
| Registration fails | pjsip show contacts; redacted authorized-client log | Check loopback 5060/UDP and private credentials; no public carrier claim |
| No inbound audio | call activity and rtp_ingestion/voice_trace, authorized client waveform | Check negotiated PCMU/8 kHz, SDP/RTP peer/address, loopback ports; do not change proven routing blindly |
| STT timeout | content-free stt_provider/voice trace; worker health/logs | End failed session, check one worker/known bg or en, CPU/memory; no transcription injection |
| Qwen timeout | private health, compact benchmark receipts, model volume and memory pressure | Cancel/end affected turn; inspect capped CPU/RAM, then restart only idle Qwen if necessary; no automatic business-action retry |
| TTS fails | tts_provider trace and scoped worker log | Verify existing pinned BG38 cache; replay no booking tool; no automatic Ivan default replacement |
| Playback fails | output_packet_sent and caller receive WAV | Check RTP direction/codec/sequence; a nonempty WAV does not prove intelligibility |
| Booking tool fails | scoped approval, tool execution and committed appointment lookup | Do not announce success; verify existing result/idempotency before any manual retry |
| Database fails | read-only integrity/foreign-key check, backend readiness | Stop owned writer before maintenance; preserve files; use authenticated fresh-target recovery, never overwrite live SQLite |
| Dashboard stale/refused | exact http://127.0.0.1:3011/dashboard listener/HTTP, UI error and existing bounded poll | Use correct local port, check frontend/backend separately; owner visually verifies rows; do not bypass browser policy |
| Memory pressure | owned cgroup memory.max/events/peak, CPU samples, host headroom | Keep one call and one model/worker per service; close owner-controlled unnecessary work, no allocation of all 16 GB to Docker |

Actual receipt locations: artifacts/phase8b/sip-tests/<attempt>/result.json, client-redacted.log, received.wav, resources.json; artifacts/phase8b/cgroup-memory-final.json; artifacts/phase9/readiness.json. Live transcript/recording defaults remain off; diagnostic traces contain metadata only.

Cached wait/error speech is a fallback, not booking success. If persistence succeeded but playback failed, disclose the delivery failure and retrieve the existing booking ID rather than creating another. Recovery procedures are prepared; a Phase 9 fault-injection/live recovery rehearsal was not performed while the prerequisite gate was blocked.
''')
    write('PHASE9_ACCEPTANCE_RESULTS.md',f'''# Phase 9 acceptance results

{blocked}

## Prerequisite evidence checked

Phase 8B actual attempts: 20261009T105422Z-29fa08 (BG), 20261009T105839Z-e5d106 (EN), 20261009T110159Z-7f0d1a (BG). Golden business rows and response packets passed; three distinct appointments survived restart. Human-heard confirmation and visual dashboard fields remain false/pending. The question acoustic control failed. Earlier unsuccessful Phase 8 attempts remain retained.

{blockers}

## Newly run preparation verification

{observed}. Fresh frontend nine tests/typecheck/lint/build pass; actual logs are artifacts/phase9/frontend-*.txt. New reset and readiness tests use disposable stores; other/unmarked tenants and active calls are protected, seed fixtures survive repeated archival reset, and healthy/business evidence cannot waive human or acoustic gates. One new test initially referenced audit_records instead of the existing audit_events table; it failed and was corrected before the passing full suite. The original reset regression was updated to assert the now-required seed preservation behavior, not to bypass failed acceptance.

The read-only runtime audit returned DEMO_BLOCKED with database integrity ok, zero foreign-key errors, schema 5 and existing configured resources. Fixed future slots were checked using the current mock calendar rules and persisted appointment reads; no reservations were created. Four isolated offline messaging scenarios passed; no real send or live dashboard notification was produced.

## Not performed

No new Phase 9 live SIP calls, human listening certification, visual UI inspection, live reset, live restart rehearsal, provider send, RC branch/tag/commit, remote push or public deployment. Reset source changes are prepared, not deployed to the live image. This is not a new three-call acceptance streak or production validation.

Release decision: **DEMO_BLOCKED**. Do not relabel mandatory voice/persistence/UI failures as limitations. Obtain new actual evidence after correcting the prerequisite issues, then run the full release-candidate workflow.
''')
    historical=json.loads((ROOT/'artifacts/phase8b/three-call-results.json').read_text(encoding='utf-8'))
    perf='''# Demo performance evidence

DEMO_BLOCKED. No new Phase 9 live voice or Qwen benchmark was run. The table below is explicitly historical Phase 8B data from 9 October 2026, not a newly accepted rehearsal. Subsequent Phase 9 synthetic fixed-date TTS/STT probes are recorded separately; they do not establish live or human acceptance.

| Historical call | Locale | Confirmation STT ms | Consent decision ms | Confirmation TTS ms | Finalized speech → first confirmation packet ms |
|---|---|---|---|---|---|
'''
    for r in historical:
        events=r['operations_snapshot']['voice_trace'];decision=next(e for e in events if e.get('call_id')==r['call_id'] and e['stage']=='confirmation_evaluated')
        group={e['stage']:e for e in events if e.get('correlation_id')==decision['correlation_id']}
        perf+=f"| {r['attempt_id']} | {r['locale']} | {group['stt_final']['duration_ms']:.2f} | {decision['duration_ms']:.3f} | {group['tts_completed']['duration_ms']:.2f} | {group['output_packet_sent']['duration_ms']:.2f} |\n"
    perf+='\nFirst synchronized human-audible latency and SIP connection duration were not separately measured; no number is invented. Registration/CONFIRMED evidence is retained in the redacted client logs. Model intent/native-tool proposal and existing agent/tool aggregate timings remain in each actual Operations snapshot. Separate compact Qwen probes are historical, not per-call decoder throughput.\n\nSampled Docker CPU maxima over the three historical calls (100% corresponds to one core-equivalent; sampling can miss peaks):\n\n| Service | Maximum observed CPU % |\n|---|---|\n'
    cpus={}
    for r in historical:
        samples=json.loads((ROOT/'artifacts/phase8b/sip-tests'/r['attempt_id']/'resources.json').read_text())
        for sample in samples:
            for row in sample.get('samples',[]):
                name=row['Name'];value=float(row['CPUPerc'].rstrip('%'));cpus[name]=max(cpus.get(name,0),value)
    perf+='\n'.join(f'| {name} | {value:.2f} |' for name,value in sorted(cpus.items()))
    perf+='\n\nHistorical cgroup charged peaks: Qwen 4,294,967,296 bytes; STT 738,668,544; TTS 1,921,519,616. Peaks cover different service lifetimes/startup/cache/kernel, not simultaneous total RAM. No OOM kill or automatic service restart was observed; Qwen hit its 4 GiB cap. CPU/background workload and development checks varied, so no capacity/SLA guarantee follows. One call and one inference process per service remain.\n\nUse VOICE_LATENCY_RESULTS.md, actual per-call Operations/resources and cgroup-memory-final.json. Development-only Ivan evaluation is much faster in batch, but the active response TTS remains BG38; no production default change is approved. First-audible, fixed-date voice and 8–12-minute presentation timing require a new attended rehearsal after the prerequisite gate passes.'
    write('DEMO_PERFORMANCE.md',perf)
    items=[('Application build','VERIFIED','fresh frontend-build.txt','frontend','No live UI certification'),('Backend tests','VERIFIED',observed,'backend QA','Rerun after any further code change'),('Frontend tests','VERIFIED','9 fresh tests/lint/typecheck/build','frontend QA','Human visual evidence remains'),('Docker health','HEALTHY','readiness.json component probes','demo operations','No whole-workflow inference from health'),('SIP registration','BLOCKED','historical Phase 8B registered calls only','telephony','New attended rehearsal after gate'),('Qwen inference','HEALTHY','loaded worker + historical probes','inference','New fixed-date performance rehearsal'),('Bulgarian STT','BLOCKED','question false consent in stt-matrix.json','speech','Correct and validate acoustic safety'),('Bulgarian TTS','BLOCKED','actual WAV/RTP, listening pending','speech/owner','Human intelligibility/date/name review'),('English STT/TTS','BLOCKED','historical EN business success; listening pending','speech/owner','Complete attended acceptance'),('Agents/tools/tenant','VERIFIED','readiness + fresh regression suite','backend','Live scoped dashboard action verification'),('Booking persistence','VERIFIED','historical 3 IDs/restart + fresh deterministic tests','backend','Fresh release rehearsal'),('Dashboard visibility','BLOCKED','HTTP 200, owner visual check pending','frontend/owner','Inspect actual call/conversation/agent/tool/appointment'),('Demo seed','VERIFIED','idempotent marked tenant; two dentists/templates','demo operations','Do not duplicate or change original seed date'),('Demo reset','BLOCKED','disposable repeat/scope/active-call tests pass','demo operations/owner','Explicitly confirmed operational rehearsal; not run live'),('Presenter scripts','PREPARED','BG/EN scripts + fixed demo-plan.json','presenter','Rehearse numeric date speech and 8–12 min timing'),('Fallback','PREPARED','existing bilingual Web Chat; isolated mock artifact','presenter','Label fallback/recorded evidence honestly'),('Notifications','NOT_CONFIGURED','no live tenant connections; templates/offline mock fixture','messaging','Simulated preview only; no external send'),('Release source','BLOCKED','Git commit/RC ID null; documented untracked source','repository owner','Review and freeze source only after gate passes')]
    checklist=f'# Demo release checklist\n\n{blocked}\n\nVerification date: {verified}. VERIFIED applies only to the named evidence scope. PREPARED/NOT_CONFIGURED are checklist states, not successful live acceptance.\n\n| Item | Status | Evidence | Last verified | Responsible component | Remaining action |\n|---|---|---|---|---|---|\n'
    checklist+='\n'.join(f'| {a} | {b} | {c} | {verified[:10]} | {d} | {e} |' for a,b,c,d,e in items)
    checklist+='\n\nNo mandatory failed item can be converted to DEMO_READY_WITH_LIMITATIONS. The actual runtime, test, inventory and acceptance evidence is under artifacts/phase9; historical live evidence remains distinctly under artifacts/phase8b.'
    write('DEMO_RELEASE_CHECKLIST.md',checklist)
    marker='## Phase 9 — blocked release preparation'
    path=ROOT/'docs/architecture/IMPLEMENTATION_STATUS.md'
    original=path.read_text(encoding='utf-8').split(marker)[0].rstrip()
    path.write_text(original+'\n\n'+marker+'\n\n'+blocked+'\n\n'+observed+'. Fresh frontend nine tests, lint, typecheck and build pass. Read-only health/inventory, fixed dated plan, bilingual presentation/recovery/checklist documents and isolated reset safeguards are prepared. The reset preserves seeded fixtures, rejects active/foreign/unmarked tenants and requires explicit CLI/PowerShell confirmation; live data was not reset. No RC, commit/tag, public release, deployment, new live rehearsal or real send was performed. See docs/demo/PHASE9_READINESS.md for exact blockers and evidence.\n',encoding='utf-8')
    print('Created ten Phase 9 demo documents and updated implementation status; decision DEMO_BLOCKED.')


if __name__=='__main__':main()
