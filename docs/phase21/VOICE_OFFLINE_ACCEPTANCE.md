# Voice fixture acceptance checkpoint

Existing VoiceSessionManager,VoiceGateway/VoiceStream/audio/RTP and receptionist/executor reused. Added bilingual fixture: complete booking→explicit mock speak transition→barge-in→same final utterance replay→terminate; appointment unchanged and exactly one CreateAppointment execution. Initial test attempted barge-in while listening and correctly received409; fixed fixture now passes, no transition policy loosened.

Full351backend testsPASS includes existing final-vs-partial,no duplicate/cross-tenant,barge-in responsive reader,timeout/termination,consent/privacy/retention and mock BG/EN speech contracts. These are fixtures, not real ASR/TTS/SIP/heard acceptance. Model services remain stopped; no waveform/reference recording/model inference/download/paid API or public endpoint used.

Fresh Phase21ASR WER/RTF,neural first-audio/intelligibility/end-to-end latency/peak model memory/concurrent actual calls: NOT_TESTED. Existing historical synthesis/call reports remain dated and incomplete. No natural/real-time/production voice claim. Reuse license comparison and Phase20real-model execution gate before any actual worker benchmark.
