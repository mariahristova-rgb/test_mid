# Scoped failure recovery

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
