# Phase21 entry and architecture audit

13October2026, Europe/Sofia. Read-only runtime inspection; implementation awaiting reviewed plan. Current clean starting checkpoints: assistant5b4cd46,website d7fab0b on codex/phase20-deployment-readiness. Phase20source/audits and Phase19test evidence do not certify voice or production. No model/service started, downloaded or installed; no customerDB/credentials read.

| Capability | Classification | Evidence / gap |
|---|---|---|
| Shared two-agent orchestration,tools,booking persistence | Implemented and tested | orchestration.py,booking.py,tools.py,store.py; Phase19synthetic346tests,36corpus |
| Calendar/Gmail lifecycle and uncertainty | Implemented but incomplete | concierge.py/google_workspace.py,typed widget actions, durable jobs; public/live gates remain |
| No-code drafts/test/publication | Implemented and tested | ux.py,SetupView.vue,test_ux.py; tenant-wide activation warnings and WebChat/mock restrictions |
| Complete business catalogue/policies | Missing in current setup contract | Business model has name,website,industry,timezone,weekdays,hours,one service/duration; lacks holiday/unavailable periods,prices/contact/description and cancellation-policy configuration |
| BG/EN FAQ,voice settings,channels,widget branding | Implemented but incomplete | Existing config/UI; configured channel/voice is not live readiness |
| Local Qwen | Implemented but incomplete | qwen.py,CPU compose,existing cache reports; runtime currently stopped and real model quality/latency unresolved |
| VAD/STT/TTS/audio/SIP pipeline | Implemented but incomplete | audio.py,rtp.py,voice.py,voice_gateway.py,voice_stream.py,asterisk.py,local_speech.py,neural_voice.py; native partial STT unavailable; heard acceptance unresolved |
| Operator handoff/assignment/status/redacted traces | Implemented and tested | Existing Inbox/Health/Quality/Operations; no guaranteed online human or live voice transfer |
| Contact linking | Implemented but incomplete | messaging_api.py LinkContacts:operator confirmation+free-text evidence; not customer email/phone verification or cross-channel consent capability |
| Verified customer context continuation | Missing | No verified scoped challenge/consent/resume/revoke workflow identified; never treat operator link or name/phone/email string as customer identity proof |
| Multi-owner Google/business integration | Requires architectural approval | Current Google owner pin/primary policy supports the authorized owner; arbitrary business-owner rollout is not established |
| New persistence/public contracts | Requires architectural approval | Reuse generic JSON/event store proposed; no DDL or new public endpoint before contract review |
| Public browser,model runs,live calls/customer pilot | Blocked by authorization | Phase20gates persist; no live calling/recording/paid speech/public SIP |

## Actual hardware/runtime checkpoint

Windows11Pro; Ryzen7 5700U,8cores/16logical;15.35GiBphysical RAM,2.86GiBfree at query. AMD integrated Radeon reports536870912adapter bytes; this is not dedicated GPU/CUDA evidence. CPU path only. C:23.18GiBfree,D:39.95GiBfree. Docker reports16CPUs/7,983,759,360memory bytes (~7.44GiB), not the proposed10GiB allocation.

Scoped docker ps: no running testmid-cpu-voice services; docker ps -a shows backend/frontend/widget/website/Asterisk/STT/TTS/Qwen exited255. Exit status alone does not diagnose why; stopped runtime cannot supply a fresh latency/intelligibility result. No service restart or resource change performed. Historical CPU/model/speech artifacts are referenced by docs/demo, not rehashed or loaded here.

Commands: git status/branch/log; bounded source reads of ux.py,domain.py,SetupView.vue,messaging_api.py,voice/audio/speech adapters and existing demo reports; CIM CPU/OS/RAM/video inventory; scoped Docker metadata/resource limits. Original semantic_os_for_ai remains untouched. No fresh model/audio benchmark or production KPI claimed.
