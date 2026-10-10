# Voice audio pipeline — Phase 8

The existing route remains Windows PJSUA → authenticated Asterisk endpoint 1001/extension 2000 → private ARI ExternalMedia → RTP PCMU payload type 0 → 160-byte/20 ms frames → VAD → mono PCM16/16 kHz STT → shared Qwen agents/tools → local TTS → PCMU/8 kHz paced RTP → caller.

RTP peer/SSRC/version/payload/sequence/gap checks and bounded 128-packet transport queue are preserved. Output timestamps advance by 160 at 8 kHz and sequence wraps modulo 65536. Runtime queue remains four turns; model/provider work stays in workers. Epoch changes stop obsolete paced playback and reject stale work. No external SIP or inference exposure is added.

Confirmed defect: pre-patch VAD discarded quiet audio before its first active frame and split saved long requests into two finals. The 200 ms pre-roll is bounded to 500 ms maximum, cleared on stream/format identity change, and included in existing utterance-size limits. Demo silence window 1800 ms was the first tested window retaining all seven saved fixtures as one final. It adds endpoint latency; correctness is measured before pursuing 2-second aspirations.

Current neural TTS produces actual 8 kHz PCMU after bandlimited 24→8 kHz conversion. Windows Ivan evaluation produced valid mono PCM16/16 kHz WAVs offline; it has not replaced the live provider. Original wideband speech and telephone conversion were compared through the same STT service. Narrowband loss remains a distinct issue.

Nonempty WAV, RTP transmission and human audibility are separate gates. Generated waveform headers/duration are measured; earlier real caller receive WAVs prove transport, while human listening and new Phase 8 caller confirmation must be separately verified. Recording/transcript defaults stay off; only controlled synthetic corpora and test-client receive WAVs are retained.
