# Phase 7 readiness audit — 2026-10-08

## Current Phase 7D update, 2026-10-09

The table below preserves the initial audit. Source/model/host blockers have since been investigated: the supplied GCS model is verified, separately quantized and CPU-loaded; Asterisk/ARI, Windows SIP signaling and non-silent RTP are tested. Both agents route through Qwen and enforce existing permissions/confirmation/idempotency. Local multilingual STT and actual BG/EN neural synthesis are provisioned. Complete speech/booking acceptance remains incomplete, with timeouts and ASR failures recorded rather than fabricated successes. Latest full backend suite: 204 tests passed in 104.136 seconds. Frontend typecheck/lint/build and 9 tests passed; redacted source scan passed after removing a preview-only hardcoded fixture token. See LOCAL_DEMO_READINESS, LIVE_CALL_TEST_RESULTS and all Phase 7D reports for current evidence.

## Initial audit (historical)

Initial inspection is based on source and runtime checks, not the claim that Phase 6C is complete. All work stays inside test_mid.

| Component | Initial classification | Location/config/dependencies | Verification and actual result | Remaining issue |
|---|---|---|---|---|
| Backend/conversations | VERIFIED_WORKING (automated) | assistant/api.py, store.py; SQLite migrations 1–5 | Prior complete 177-test suite; fresh rerun started | Live voice not covered by this label |
| Receptionist/executor | MOCK_ONLY for inference | orchestration.py, booking.py; ProviderRegistry.llm | Source inspection: both use deterministic workflow; Qwen not routed | Wire shared Qwen provider |
| Booking | VERIFIED_WORKING (local mock calendar) | tools.py, calendar.py; tenant DB transactions | Existing confirmation/idempotency/tenant tests | Demo hours/resources need explicit configuration |
| Qwen | IMPLEMENTED_UNVERIFIED | qwen.py; owner endpoint, httpx | Offline protocol tests only | Exact model location/version/tokenizer/runtime/host unknown |
| GCS loader | IMPLEMENTED_UNVERIFIED | model_artifacts.py; ADC, optional google-cloud-storage | Synthetic checksum/cache tests pass | Actual bucket/prefix/manifest/IAM not provided |
| SIP/PJSIP | INCOMPLETE | No Asterisk source/config/service found | Source scan; no registration evidence | Add private deployment and ARI bridge; actual softphone test |
| RTP gateway | INCOMPLETE | voice_stream.py currently WebSocket transport | Bounded workers/VAD and synthetic transport tests exist | Add RTP/ARI transport |
| STT/TTS | MOCK_ONLY | providers.py synthetic fixtures; live_voice.py gated managed adapters | No local speech artifacts/adapter | Local models and real bilingual audio acceptance required |
| Bulgarian TTS | BLOCKED | No accepted installed voice | Piper catalog metadata only; Dimitar/Lessac lineage unresolved | Approved artifact/license and listening test |
| Call sessions/cleanup | VERIFIED_WORKING (automated synthetic) | voice.py, voice_stream.py | Existing lifecycle/isolation/cleanup tests | Cancel obsolete model requests and preserve call ID |
| Dashboard | VERIFIED_WORKING (previous local tests) | Vue frontend existing persisted-data views | Phase 5 checks; no fresh SIP call data | Verify actual live call/booking rendering |
| Docker/runtime | IMPLEMENTED_UNVERIFIED for this phase | semantic_os/docker-compose.yml; backend/frontend only | No Asterisk service; Docker socket denied by sandbox on first check | Inspect daemon outside sandbox; no live stack assumed |
| Performance/live journeys | BLOCKED | No real speech/Qwen/SIP evidence | Zero measured live journeys | Need configured target; three consecutive live bookings |

Shortest path: route shared Qwen through the existing receptionist/tool executor; add explicit local speech contracts; reuse VoiceRuntime with a bounded private RTP transport and Asterisk ARI; seed a dedicated fictional tenant; run automated contracts, then real model/audio/softphone validation. No weights are downloaded during calls. Missing source/artifact information has been requested from the owner. Classification updates and final test outcomes will be recorded below as implementation proceeds.
