# Deployment readiness proposal

Reuse semantic_os/deploy/compose.cpu-voice.yml and optional reviewed neural override; no deployment/start here. Current host audit is the dated Phase21checkpoint: Windows11Pro,Ryzen5700U8cores/16logical,15.35GiBRAM,2.86GiBfree,Docker7.44GiB; integrated Radeon is not CUDA/confirmed dedicatedVRAM. Voice containers were stopped. No new capacity/live-health claim.

Configured source: Qwen3-4B-Q4_K_M.gguf at /models via existing read-only qwen_cache,4096context,4threads,1slot,0GPU; multilingual Whisper-small CPUint8 from required reviewed cache; eSpeak or reviewed BG38/MioCodec/WavLM worker. Model paths/digests/licenses must be revalidated before approved loading. Secret-file references stay server-side; no values read/copied. Reuse Phase21license matrix,with unresolved exact dependency/reference/commercial clearance limitations.

One isolated backend owns SQLite/agents/jobs; models and PBX are separate local services. Compose limits Qwen4GiB,STT1200MiB,baselineTTS256MiB; neural override is larger. Resource limits are configuration,not measured simultaneous peak. Start one approved synthetic session only after memory feasibility; no WSL/restart/allocation/replica changes implicitly.

Before any approved run: verify artifact integrity,no hidden download,health/warmup,private network/loopback binds,bounded audio/timeouts,one session,redacted logs,graceful stop and original DB/cache backup custody. Current restart:no prevents implicit voice-model restart. Model/provider failures must return truthful unavailable/unknown states,not repeat writes. Do not copy real customer data into harness.

No multi-instanceSQLite/HA claim. Distributed persistence/queue/locks,migration and restore design needs independent approval before scaling. Existing staging deadline14October20:57Europe/Sofia unchanged; that small FAQ host is not a voice inference host.
