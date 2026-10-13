# Existing SIP/PBX integration and security assessment

Reuse Asterisk→ARIbridge→RTPAudioTransport→VoiceRuntime→existing agents/tools→TTS/playback. No second PBX assistant. Current configured extension2000/endpoint1001 are internal identifiers,not public phone numbers or customer proof. Generated private SIP configs were not read; authentication values remain secret-file refs.

Compose publishes SIP5060UDP/RTP10000–10099 only on127.0.0.1; ARI remains private and Qwen loopback/private. Fresh73fixture suite includes mocked ARI/RTP/local-engine bounds and voice routing/signature/session controls; no PBX process,network telephone call or TLS/SRTP negotiation tested.

Future security gate: validate actual build/modules/credentials,certificate trust,TLS signaling and SRTP/media independently,allowlisted inbound routing,tenant mapping,ARI least privilege,connection/rate/duration/audio limits,NAT/advertised address/disconnect cleanup and no premium/outbound dialing. CallerID alone never proves customer identity. [Official PJSIP configuration](https://docs.asterisk.org/Asterisk_20_Documentation/API_Documentation/Module_Configuration/res_pjsip/) documents TLS/SRTP options; availability of options is not evidence they are configured here.

Asterisk is already integrated; switching to FreeSWITCH/WebRTC adds unmeasured work and is not selected. Any public connectivity,number/trunk/account/provider/routing/budget/caller/consent policy requires exact separate approval. Ordinary telephone service may have fees even when AI inference is self-hosted. No number purchased,port exposed or toll service enabled.
