# Local SIP setup and actual findings

Account 1001 is the fictional caller; extension 2000 enters Stasis testmid-voice. The SIP password is in the protected artifacts/local-demo/secrets/sip_password.txt; the separate ARI password is never sent to the softphone. Use Linphone or a compatible Windows softphone with PCMU/8 kHz and server 127.0.0.1:5060.

An official PJSUA 2.17 client was cross-compiled from upstream commit 5a457451fa2712ba18e12b01738e8ff3af2b26fd and exported to artifacts/sip-client. Actual Windows registration returned status 200, actual calls reached 2000 and created tenant-scoped Asterisk CallSessions, and disconnect released channels/sessions. This is real signaling, not a mocked registration.

Initial recordings were silent. Actual SDP advertised an unreachable container address; packet diagnostics showed incorrect loopback handling. The dedicated endpoint now explicitly uses transport-udp and media_address=127.0.0.1 with bind_rtp_to_media_address=no. The corrected Windows test transmitted about 1.3K RTP packets and recorded nonzero greeting samples. The generator preserves this fix. RTP peer validation remains pinned to authenticated ARI metadata for the private ExternalMedia channel.

The harness uses generated fictional WAVs and a null audio device; no microphone/patient recording is enabled. This does not establish human speech quality or a completed booking journey. TLS/SRTP is not active in the local UDP test. Public/LAN deployment requires a separately verified secure transport/network design.
