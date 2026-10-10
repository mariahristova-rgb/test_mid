"""Summarize preserved measured Phase 8 evidence without inferring acceptance."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def append(relative, text):
    path = ROOT / relative
    marker = '## Phase 8 measured outcome — 9 October 2026'
    previous = path.read_text(encoding='utf-8').split(marker)[0].rstrip()
    path.write_text(previous + '\n\n' + marker + '\n\n' + text.strip() + '\n', encoding='utf-8')


def main():
    results = json.loads((ROOT / 'artifacts/phase8/three-call-results.json').read_text(encoding='utf-8'))
    if len(results) != 3:
        raise RuntimeError('Three actual attempts must finish before final reporting')
    rows = []
    for row in results:
        phases = row.get('phases', [])
        state = phases[-1].get('actual_state', {}).get('status', 'unknown') if phases else 'unknown'
        timings = '/'.join(str(round(p['wall_ms'])) for p in phases)
        rows.append(f"| {row['locale']} | {row['attempt_id']} | {row.get('call_id')} | {state} | {len(row.get('booking_ids', []))} | {timings} |")
    table = '| Locale | Attempt | Call ID | Last booking state | New confirmed bookings | Request/name/confirm observation ms |\n|---|---|---|---|---|---|\n' + '\n'.join(rows)
    outcome = '''**PARTIAL / BLOCKED.** Three real SIP attempts finished, but the booking release gate did not pass. Registration, call establishment and response packets are separate from caller-heard confirmation. Known locale was selected through the existing authenticated call-language control; no STT transcript was injected. Synthetic WAV callers were used, not representative human callers. Raw live transcripts remain disabled by the existing privacy settings.

''' + table + '''

Each attempt retains its input hashes, received WAV, redacted signaling, resource samples, conversation, agent handoffs and tool results under artifacts/phase8/sip-tests/<attempt>/. The summary is artifacts/phase8/three-call-results.json. State observation timings include input playback, buffering, inference and polling; they are not synchronized first-audible latency. No new correct booking or three-call success is inferred. The prior correct English booking remains historical evidence, not a Phase 8 pass.

Required remaining gates: reliable telephone-band time/consent recognition, caller-heard intelligibility, real in-call language switching/unavailable/interruption/failure scenarios, visual dashboard verification and three consecutive complete correct bookings. Existing unit tests do not establish those live gates. Browser security policy rejected local dashboard inspection; no indirect or alternate-browser bypass was attempted.'''
    for relative in ('docs/demo/THREE_CALL_ACCEPTANCE.md', 'docs/demo/BILINGUAL_LIVE_ACCEPTANCE.md'):
        append(relative, outcome)
    append('docs/demo/PHASE8_ROOT_CAUSE_ANALYSIS.md', '''The runtime recovered through the existing Docker Desktop CLI and project-scoped Compose startup. Only the backend image was rebuilt for targeted fixes; the existing Qwen, STT and TTS models were preserved.

Actual frame replay confirmed two defects: missing quiet onset and one booking request split into two turns by the old 600 ms endpoint. A bounded 200 ms pre-roll and a demo-only 1800 ms silence setting retain one turn in all seven saved fixtures; 1200 ms still split Bulgarian. The platform default is preserved. Clear required Bulgarian reservation confirmation is supported. Model-only cancellation guesses now retain the proposal and request clarification unless literal caller cancellation is present. The name guard excludes the recognized standalone prefix “са”. Negations, questions and corrupted affirmative phrases are not repaired into consent.

The required synthetic corpus still fails Bulgarian clock and confirmation recognition. Windows Ivan evaluation recognized the clock correctly at original 16 kHz, then failed after 8 kHz PCMU conversion; bandlimited upsampling did not restore it. This is evidence of narrowband recognition loss, not proof that the live caller said any particular transcript. TTS replacement alone is insufficient.

208 backend tests passed in 57.674 seconds; frontend typecheck/lint/nine tests/build passed; 158 source/config files passed the boundary check. A network-disabled redacted Gitleaks scan of 249 staged source/config/docs files found no leaks. Host memory pressure and unrelated background workloads limit performance conclusions.

''' + outcome)
    append('docs/demo/BULGARIAN_TTS_VALIDATION.md', '''**Bulgarian TTS acceptance remains incomplete.** Four mandatory output phrases and five recognition phrases were actually synthesized through the existing CPU BG38/MioCodec adapter. All waveforms and actual round-trip transcripts are retained in artifacts/phase8/speech-corpus; no expected text is substituted for an observed result. The telephone-band “петнадесет часа” and reservation confirmation are corrupted by STT. Nonempty audio is not human intelligibility evidence.

An evaluation of the already-installed Microsoft Ivan voice produced seven real 16 kHz PCM waveforms. Cold full synthesis was 360.973 ms; warmed full synthesis was approximately 13–22 ms. Evaluation-process working set was 104,607,744–108,703,744 bytes. These are host SDK evaluation measurements, not deployed-service or SIP measurements. Waveforms, timings and pronunciation checks are retained under artifacts/phase8/windows-voice. The original wideband clock was recognized as “Искам час в 15 часа.” in 12,116.36 ms; bandlimited telephone round-trip returned “Из към час, бъпет наися часа.” in 6,104.19 ms. Human listening remains pending.

[Microsoft documents Bulgarian Ivan](https://support.microsoft.com/en-us/accessibility/windows/narrator/appendix-a-supported-languages-and-voices). Installed Windows voices are proprietary Microsoft components, not Ontelyx semantic runtime components. No voice assets were downloaded or redistributed. Commercial deployment rights under applicable Windows terms have not been certified. A private authenticated local-demo bridge was proposed, but has not been activated: Phase 8 explicitly requires owner approval before major TTS replacement, and that answer remains pending. The current licensed-model declarations and existing worker are preserved.

''' + outcome)
    append('docs/demo/VOICE_LATENCY_RESULTS.md', '''Actual Phase 8 synthetic corpus: STT HTTP wall time 4,863–7,224 ms; existing batch TTS total 1,764–13,819 ms. These ranges cover fourteen mixed Bulgarian/English synthetic cases, not a human recognition benchmark or streaming vocoder. Receipts: artifacts/phase8/speech-corpus/results.json.

Real compact Qwen structured probes passed in both languages. Bulgarian first visible token 17,735.45 ms / total 20,065.52 ms / 0.349 completion tokens per second over request wall time; English 5,314.64 / 8,403.25 / 1.190. Timestamped compact receipts are preserved in artifacts/local-demo. These are observed CPU requests under host memory/background load, not isolated decoder throughput.

Windows Ivan offline candidate: cold full synthesis 360.973 ms, warmed approximately 13–22 ms. The candidate is not deployed and does not establish end-to-end latency. First caller-audible confirmation and per-call latency percentiles remain unverified.

''' + outcome)
    append('docs/architecture/IMPLEMENTATION_STATUS.md', '''Phase 8 adds bounded audio pre-roll, a demonstrated demo-only VAD endpoint correction, clear Bulgarian reservation consent, guarded literal cancellation and safer name-prefix handling. Existing tenant-scoped agents, tool permissions, approval/idempotency, conversations and mock calendar remain. Original Qwen3-4B BF16 artifacts are preserved; the existing derived Q4_K_M model is unchanged. No paid managed provider, larger LLM or Ontelyx proprietary semantic runtime was introduced.

Verification: 208 backend tests passed (57.674 s); frontend typecheck/lint/nine tests/build passed; source boundary check 158 files/zero failures; redacted offline secret scan 249 staged files/zero findings. Required Phase 8 documentation and actual audio/call evidence are present. Commercial deployment and live-demo readiness are not claimed.

''' + outcome)
    cleanup = json.loads((ROOT / 'artifacts/phase8/cleanup-operations.json').read_text(encoding='utf-8'))
    metrics = cleanup['operations']['metrics']
    metric_rows = '\n'.join(
        f"| {name} | {metrics[name]['count']} | {metrics[name]['mean_ms']:.2f} | {metrics[name]['max_ms']:.2f} |"
        for name in ('stt_provider', 'tts_provider', 'voice_turn', 'utterance_to_ack_first_packet', 'utterance_final_to_first_output_packet', 'rtp_ingestion'))
    latency = ROOT / 'docs/demo/VOICE_LATENCY_RESULTS.md'
    with latency.open('a', encoding='utf-8') as stream:
        stream.write('\nFinal backend-lifetime operational snapshot (not per-call percentiles):\n\n'
                     '| Stage | Count | Mean ms | Max ms |\n|---|---|---|---|\n' + metric_rows + '\n\n'
                     'Three call timeout/error events were recorded. Cached acknowledgement delivery averaged about 6.10 seconds; '
                     'business output averaged about 34.01 seconds after finalized audio. Neither is a guaranteed SLA. '
                     'Evidence: artifacts/phase8/cleanup-operations.json. RTP ingestion stayed separate from inference.\n')
    memory = json.loads((ROOT / 'artifacts/phase8/cgroup-memory-final.json').read_text(encoding='utf-8'))
    mem_rows = '\n'.join(f"| {r['service']} | {r['peak_bytes']} | {r['current_bytes']} | {r['memory_events']['max']} | {r['restart_count']} | {r['oom_killed']} |" for r in memory['services'])
    append('docs/demo/MEMORY_OPTIMIZATION_RESULTS.md', '''Final cgroup measurements include startup/cache/kernel and have different service lifetimes. Individual peaks are not a simultaneous aggregate RAM peak. No sampled service had an OOM kill or automatic restart; Qwen nevertheless reached its 4 GiB cap and recorded memory-max pressure.

| Service | Charged peak bytes | Current bytes | Memory-max events | Automatic restarts | OOM killed |
|---|---|---|---|---|---|
''' + mem_rows + '''

Evidence: artifacts/phase8/cgroup-memory-final.json. CPU cumulative counters and throttle counts are preserved there; per-attempt CPU/memory samples are in each SIP resources.json. Earlier sampled swap and host headroom are not final peak measurements. Increasing Docker allocation or changing Qwen cache settings was not demonstrated safe on this loaded 16 GB host.''')
    append('docs/demo/DEMO_OPERATIONS.md', f'''Three actual calls completed with zero active API call sessions ({len(cleanup['active_call_ids'])}) and zero Asterisk active channels/calls. The Asterisk diagnostic recorded three calls processed. Caller processes exited normally. Existing persisted bookings remain; these Phase 8 attempts created none. Evidence: artifacts/phase8/cleanup-operations.json and three per-call result files.

All required reports now preserve the measured failures and open gates. Service health, zero active channels and passing regressions do not establish demo readiness. Existing services are retained for owner review; no unrelated container was stopped. The major TTS replacement remains pending explicit Phase 8 approval.''')
    print('Updated six reports from three preserved actual SIP attempts; status PARTIAL / BLOCKED.')


if __name__ == '__main__':
    main()
