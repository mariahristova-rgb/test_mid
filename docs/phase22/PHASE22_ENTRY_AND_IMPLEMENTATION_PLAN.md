# Phase22 entry and proposed implementation plan

13October2026. **ENTRY_BLOCKED for full implementation.** Phase21first no-code/fixture increment approved and executed; fullPhase21foundation not verified. Phase22prompt does not waive separate continuity/model/API review or authorize runtime optimization. No Phase22runtime changes performed.

## Entry matrix

| Capability | Verdict | Source evidence |
|---|---|---|
| No-code optional business fields/BG-EN/mock rules | PASS local | Phase21UX/calendar/UI tests,351backend/37frontend/41corpus |
| Existing voice pipeline/adapters/session/booking | PASS fixture; NOT TESTED real | Existing voice tests plus new committed-interruption regression; model containers stopped |
| Actual BG/EN WER,intelligibility,first audio,latency/resources | NOT TESTED | No new inference/synthesis/listening; historical reports not current baseline |
| Cross-channel verified identity/consent/continuity | BLOCKED | Proposed explicit contracts in Phase21doc,not implemented; operator link is not ownership |
| Human handoff/operator metadata | PASS synthetic | Existing Inbox/Health/Quality/Operations; actual human/call transfer unavailable |
| Actual concurrency/resource overload | NOT TESTED | One-session prototype only; no multiple real calls/replicas |
| Public/browser/live Google/SIP/recording/pilot | BLOCKED | Existing Phase20gates remain |

## Prioritized local plan to review

P0: review Phase21continuity challenge/confirm/context/continue/revoke contracts first. Proposed files assistant/continuity.py,api.py/widget.py/voice_gateway.py integration hooks,privacy.py and synthetic continuity tests. Reuse operations_events/conversations/contact references; no DDL/customerDB. Strict server proof/purpose/tenant/session/expiry/consent,neutral context only,fresh availability and confirmation. Unapproved proof delivery fails closed; no real sends.

P0: fixture voice create/reschedule/cancel/recovery/interruptions and two-session isolation/graceful-overload coverage. Reuse voice.py,voice_stream.py,rtp.py,calendar.py and current voice/corpus tests. Modify runtime only for demonstrated failures after plan approval. No natural/streaming/latency improvement claim from fixture timings.

P1: no-code voice selection/preview/incomplete states using SetupView.vue,VoiceConfig and approved local voice IDs. Keep activation disabled until per-capability evidence. Any additive API/settings contract requires review; no new payment/provider.

Actual speech/latency optimization is a separately gated benchmark stage: existing pinned Qwen4B Q4/Whisper-small CPUint8 and reviewed BG/EN TTS only,one session first,existing caches,explicit generic permitted reference,no cloning/download. Current hardware checkpointRyzen5700U/15.35GiBtotal/2.86GiBfree,Docker7.44GiB; do not start models or raise memory/replicas automatically. ASR final-only/chunked,not native partial; never convert publisher component benchmarks into end-to-end claims. License/source matrix reused from Phase21.

P1: existing redacted Operations/Health/Quality metrics and runbook,scenario/channel/locale/receipt IDs; no raw audio/transcripts or invented production/cost. P2telephony feasibility only: existing Asterisk/SIP/RTP adapters,NAT/codec/firewall/transfer abuse boundaries; no number/trunk/live calling/public endpoint.

## Acceptance and rollback

After approved fixture increment: targeted tests then fullbackend/frontend/website/source/migration/evaluation checks,exact evidence,unchanged schema/public contracts except explicitly reviewed additions. Review0duplicate/ownership/privacy invariants under interruption,reconnect,revocation/concurrent sessions. Store local checkpoints on separatefeaturebranches; revert only approved source increment,preserve DB/cache/committed bookings/revocations. No deploy/main merge/push or new spend.

All14Phase22deliverables will reference actual incremental evidence; do not fill speech quality/concurrency reports with mock measurements. Phase23recommendation currently NO-GO for external activation. Owner review of this plan and continuity contracts is required before Phase22runtime work. Actualmodel execution,publicbrowser,liveGoogle,recording,SIP/pilot/deployment/spending remain separately unauthorized.
