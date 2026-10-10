# Self-hosted gateway status

The existing voice manager, audio utilities and bounded worker runtime remain unchanged. They preserve the prior synthetic voice workflow; no new RTP/ARI gateway is connected.

Pending integration: validated negotiated RTP peers/codec, bounded VAD buffers, STT worker, tenant-routed shared Qwen orchestration, local TTS, paced RTP playback, barge-in cancellation, call-session correlation through handoffs and cleanup of owned ARI channels. Inference must stay outside the audio receive loop. No audio-loop, latency or cleanup result is claimed for this pending route.
