"""Append measured Phase 8B evidence; human/live gates remain explicit."""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'artifacts/phase8b'
MARKER='## Phase 8B measured update — 9 October 2026'


def load(relative,bom=False):
    return json.loads((EVIDENCE/relative).read_text(encoding='utf-8-sig' if bom else 'utf-8'))


def update(relative,text):
    path=ROOT/relative
    original=path.read_text(encoding='utf-8') if path.exists() else ''
    path.write_text(original.split(MARKER)[0].rstrip()+'\n\n'+MARKER+'\n\n'+text.strip()+'\n',encoding='utf-8')


def main():
    matrix=load('stt-matrix.json')['results']
    table='| Phrase | Variant | Actual telephone-band transcript | Pending decision | STT ms |\n|---|---|---|---|---|\n'
    table+='\n'.join(f"| {r['expected_text']} | {r['variant']} | {r['actual_text']} | {r['decision_if_pending']} | {r['wall_ms']:.2f} |" for r in matrix)
    stt='''Existing multilingual small, CPU/int8/four threads/one worker, explicit bg, no new model or expected-answer prompt. Nine owner-authorized synthetic Ivan waveforms were bandlimited to 8 kHz and PCMU encoded/decoded. Twenty-seven actual inference trials compared existing duplication/beam1, bandlimited upsampling plus 250 ms padding/beam1, and the same padding/beam3. The normal STT service was stopped only during this offline single-worker evaluation, then restored. The first harness invocation failed before inference due an import path; this was corrected and retained as a harness failure.

All nine VAD replays finalized once with the existing demo 1800 ms endpoint, RMS threshold 400 and 200 ms pre-roll. “Да” had only 260 ms above threshold. No higher minimum-duration gate was added to discard it. Padding/resampling recovered “Потвърждавам часа” but corrupted “Точно така”; no global change is justified by this corpus. No negative, rejection or ambiguous control became affirmative, but **the question control became affirmative in all three variants**. The question marks in known text are rejected by the application, yet ASR removed this punctuation. This is an actual false-positive acoustic-control failure, not safe general speech acceptance. Prosody/human recognition and broader consent validation remain open.

''' + table + '\n\nEvidence: artifacts/phase8b/stt-matrix.json and phone-fixtures/*.wav. Process peak RSS reached '+str(max(r['process_peak_rss_bytes'] for r in matrix))+''' bytes; this is not container charged peak or simultaneous whole-stack memory. The two selected caller fixtures also passed the actual backend VAD and authenticated existing STT service: “Да, потвърждавам.” and a Monday 17:00 request. Evidence: call-input-stt.json. These are synthetic fixtures, not representative human recordings.'''
    update('docs/demo/BULGARIAN_STT_VALIDATION.md',stt)
    voices=load('windows-voice-cpu/bg-BG-results.json',True)
    tts_table='| Phrase | Full synthesis ms | Process CPU ms | Working set bytes | Process peak working set bytes |\n|---|---|---|---|---|\n'
    tts_table+='\n'.join(f"| {r['text']} | {r['wall_ms']:.3f} | {r['cpu_ms']:.3f} | {r['working_set_bytes']} | {r['peak_working_set_bytes']} |" for r in voices)
    tts='''Development-only evaluation authorized by the Phase 8B request. Microsoft Ivan was found in installed Windows voices and generated nine real 16 kHz mono PCM16 WAVs through WinRT. No voice assets were downloaded, redistributed or installed. The harness records full-batch availability, process CPU time and working-set snapshots/OS process peak; these exclude CPU/memory in any separate Windows component. Full synthesis is not streaming first-audio or caller-heard latency.

''' + tts_table + '''

The Windows-generated files were transferred into the repository-owned Docker STT container, converted to PCMU telephone audio and successfully transcribed for selected affirmative/request fixtures. SHA-256 hashes and waveforms are retained. The test process loads the current trusted backend VAD source without modifying the speech image. Initial fixture preparation failed on copied-directory permissions and an older image's VAD signature; only the temporary test directory/import was corrected. These failures did not execute booking tools.

The existing BG38/MioCodec response provider remains active. Its fourteen-case Phase 8 corpus took 1,764–13,819 ms full batch synthesis; the current Ivan trial is much faster but uses different phrases/processes and is not a controlled live-service comparison. The current response voice has actual SIP output; Ivan has only host evaluation/caller-fixture output. Human pronunciation/intelligibility remains an explicit listening gate.

[Microsoft's SpeechSynthesizer documentation](https://learn.microsoft.com/en-us/uwp/api/windows.media.speechsynthesis.speechsynthesizer?view=winrt-26100) describes use of installed Microsoft-signed voices. [Applicable Microsoft license terms](https://www.microsoft.com/en-us/useterms) depend on the installed product/license. This evaluation does not certify commercial hosting, redistribution or production rights. Installed Ivan is proprietary Microsoft speech, not an Ontelyx semantic runtime dependency. The owner authorized evaluation only; no production default or private live voice bridge was changed. Further production-default approval and licensing review are separate prerequisites.'''
    current_file=EVIDENCE/'current-tts/results.json'
    if current_file.exists():
        current=json.loads(current_file.read_text(encoding='utf-8'))
        windows={r['label']:r for r in voices}
        tts+='\n\nAdditional same-phrase comparison, actual warm current-provider API versus Windows batch SDK (different interfaces and processes, not a controlled service-capacity guarantee):\n\n| Phrase | BG38 HTTP batch ms | Ivan batch ms | BG38 phone-band actual STT |\n|---|---|---|---|\n'
        tts+='\n'.join(f"| {r['text']} | {r['tts_http_wall_ms']:.3f} | {windows[r['label']]['wall_ms']:.3f} | {r.get('actual_stt',{}).get('text','no successful recognition')} |" for r in current)
        tts+='\n\nAll nine BG38 synthesis/recognition calls returned HTTP 200. Short “Да” was recognized correctly; longer affirmative and “Точно така” were corrupted and remain unapproved text. Negative and ambiguous controls never authorize booking in the exact gate. The original question control became corrupted/unclear, while the Ivan question control became affirmative. Neither a nonempty waveform nor selective correct recognition establishes general human intelligibility or speech-consent safety. Evidence: artifacts/phase8b/current-tts/results.json and actual WAVs.'
    update('docs/demo/WINDOWS_IVAN_EVALUATION.md',tts)
    update('docs/demo/BULGARIAN_TTS_VALIDATION.md',tts)
    summary=EVIDENCE/'three-call-results.json'
    results=json.loads(summary.read_text(encoding='utf-8')) if summary.exists() else []
    live='''**PARTIAL / BLOCKED.** Deterministic confirmation is recovered; complete live acceptance is not inferred. The owner declared availability for live acceptance before new SIP attempts. Caller fixtures combine existing BG38 speech and authorized Ivan evaluation speech; the assistant's response provider remains BG38. Known locale is selected through the existing authenticated control, without transcript injection.

| Locale | Attempt | Call ID | Business workflow | Booking IDs | Human-heard verification |
|---|---|---|---|---|---|
'''
    live+='\n'.join(f"| {r['locale']} | {r['attempt_id']} | {r.get('call_id')} | {r.get('business_workflow_passed')} | {', '.join(r.get('booking_ids',[])) or 'none'} | pending |" for r in results)
    live+='''

Three consecutive complete calls, human-audible correct confirmation, visual dashboard evidence and the acoustic question false-positive control remain open gates. Received RTP/nonzero WAV/persisted row alone cannot satisfy human acceptance. New receipts are artifacts/phase8b/sip-tests/<attempt>/; prior unsuccessful attempts remain in Phase 8 evidence. Sequence continuation is permitted only after the preceding business journey passes; no failure is silently omitted. Browser policy previously blocked local inspection and is not bypassed; the owner can verify the dashboard directly.'''
    if len(results)==3 and all(r.get('business_workflow_passed') for r in results):
        live+='\n\nAll three consecutive selected-affirmative SIP business journeys passed. Each created one distinct correct appointment, and response audio reached the caller transport. All three survived the targeted backend restart; no active API calls or Asterisk channels remain. Caller-side final-45-second excerpts were provided for human listening. This is business/transport evidence, not full human acceptance.'
    live+='\n\nThe owner initially reported ERR_CONNECTION_REFUSED when checking the dashboard. The intended URL is http://127.0.0.1:3011/dashboard; the existing listener was verified on 127.0.0.1:3011 and returned HTTP 200. Visual booking verification remains pending the owner’s follow-up; HTTP availability is not visual proof.'
    update('docs/demo/THREE_CALL_ACCEPTANCE.md',live)
    core='''Implemented the smallest confirmation fix: exact clear consent in an existing unexpired proposal is decided deterministically, without a second probabilistic intent veto. Executor/tool/approval authorization, fingerprint/expiry, availability and idempotency checks remain. Rejection, explicit requested slot replacement, voice expiry and disconnect invalidate an outstanding proposal; playback, segmentation, handoff and short silence retain it. Ambiguous text explicitly asks for clarification. Web Chat HTTP expiry behavior is preserved.

Content-free bounded tenant traces correlate all supported stages. Local STT is final-only; partial_supported=false is explicit. Nine new regression tests cover durable single execution/replay, rejection, ambiguous/question transcripts, expiry, requested changes, locale retention, trace privacy/tenant bounds, disconnect cancellation and rollback-safe persistence tracing. The initial full suite passed 216 tests in 47.318 seconds; the final report below reflects any later trace correction. Focused finalized voice/confirmation regressions passed 41 tests in 10.400 seconds. An earlier 215-test full run also passed; the initial targeted web expiry regression was corrected before deployment. Only the backend image was rebuilt; no inference models or working infrastructure were rebuilt.

Acoustic recovery remains partial. Twenty-seven actual PCMU trials found a question waveform transcribed as literal consent. Deterministic text safety does not fix ASR loss of interrogative meaning. No broad keyword, fuzzy spelling, negative-word dropping or expected-transcript injection was introduced. General speech consent safety and human/live verification are not claimed.

''' + live
    test_report=(EVIDENCE/'backend-tests-final.txt').read_text(encoding='utf-8')
    tested=re.search(r'Ran (\d+) tests in ([\d.]+)s',test_report)
    if tested and test_report.rstrip().endswith('OK'):
        core+=f"\n\nLatest complete backend suite: {tested[1]} tests passed in {tested[2]} seconds."
    core+='\n\nPreserved frontend verification: typecheck, zero-warning lint, nine tests and build all passed, including source/bundle environment-secret scans. Source boundary check and final staged secret scan results are recorded separately. Final backend is healthy with rollback-safe trace; the three bookings survived its restart. The current Qwen/STT/BG38 model services remain unchanged.'
    update('docs/demo/PHASE8_ROOT_CAUSE_ANALYSIS.md',core)
    update('docs/architecture/IMPLEMENTATION_STATUS.md',core)
    traces=load('three-call-results.json') if summary.exists() else []
    trace_text='''The new trace is bounded in-memory operational metadata; it is exported to each actual synthetic attempt receipt. It contains no raw customer text/audio. Correlation IDs join audio receipt/VAD/STT/locale/state/decision/agent/tool/persistence/TTS/output. Approval parent correlation is retained. Outbound packet timestamps measure delivery to the caller transport, not subjective hearing. Local partial recognition is unsupported and never fabricated.

The initial live image emitted appointment_persisted after the insert inside the transaction; each claimed live booking was independently verified through the authoritative API after commit. A follow-up instrumentation correction uses the existing after-transaction hook and verifies the committed approval/appointment before emitting this stage, so a rollback never generates a persistence claim. The new rollback regression passes. This correction does not change booking behavior or model services; its deployment/version is recorded separately from earlier receipts.

Exact current failing acoustic boundary: telephone-band ASR loses or changes some confirmation words and question punctuation, before deterministic state-aware evaluation. An additional code-level model-veto boundary was removed for literal pending consent. A successful selected affirmative does not erase negative/control failures.

''' + live
    update('docs/demo/PHASE8B_CONFIRMATION_TRACE.md',trace_text)
    latency='''STT matrix HTTP-free local inference ranged '''+f"{min(r['wall_ms'] for r in matrix):.2f}–{max(r['wall_ms'] for r in matrix):.2f}"+''' ms across twenty-seven narrowband trials. Actual VAD endpoint is 1800 ms after last active frame, plus the worker settling window; it is not included in offline inference wall time. All nine synthetic VAD replays emitted once. No global resampling/beam change was applied because quality tradeoffs were measured.

Ivan batch/CPU/working-set measurements are in WINDOWS_IVAN_EVALUATION; this candidate is not the response TTS. Trace durations distinguish STT, literal confirmation processing, agent/native tool proposal, existing tool execution, TTS and final-utterance-to-first-output packet. First synchronized human-audible response remains unmeasured. Each call retains its actual Operations snapshot and resource samples; no percentile or whole-host peak is fabricated.

''' + live
    for result in results:
        events=result.get('operations_snapshot',{}).get('voice_trace',[])
        decisions=[e for e in events if e.get('call_id')==result.get('call_id') and e['stage']=='confirmation_evaluated']
        for decision in decisions:
            group=[e for e in events if e.get('correlation_id')==decision['correlation_id']]
            latency+=f"\n\nCall {result['call_id']}, correlation {decision['correlation_id']}:\n\n| Stage | Observed duration ms |\n|---|---|\n"
            for event in group:
                if 'duration_ms' in event: latency+=f"| {event['stage']} | {event['duration_ms']:.3f} |\n"
            latency+='First outbound packet is caller-transport delivery, not a synchronized human-audible measurement. State observation timing remains separate.'
    memory_file=EVIDENCE/'cgroup-memory-final.json'
    if memory_file.exists():
        memory=json.loads(memory_file.read_text(encoding='utf-8'))
        latency+='\n\nMeasured owned-container lifetime cgroup peaks (includes startup/cache/kernel; different lifetimes, not a simultaneous aggregate or per-call RSS):\n\n| Service | Charged peak bytes | Automatic restart count | OOM killed |\n|---|---|---|---|\n'
        latency+='\n'.join(f"| {r['service']} | {r['peak_bytes']} | {r['restart_count']} | {r['oom_killed']} |" for r in memory['services'])
        latency+='\n\nQwen reached its 4 GiB cap; no OOM kill or automatic restart was observed. STT was deliberately stopped/restored for offline evaluation; backend was deliberately recreated for the targeted fixes. CPU cumulative/throttle counters are retained in cgroup-memory-final.json; per-call actual CPU/memory samples remain in resources.json. Independent regression/build tasks ran during portions of development; these measurements are not isolated capacity guarantees.'
    update('docs/demo/VOICE_LATENCY_RESULTS.md',latency)
    print('Updated eight Phase 8B reports from measured evidence; live/human/control gates remain explicit.')


if __name__=='__main__': main()
