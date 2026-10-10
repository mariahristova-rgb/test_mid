# SIP setup status

No Phase 6C Asterisk deployment, PJSIP configuration or extension registration has been implemented. Existing Phase 3 managed/synthetic telephony is not the requested self-hosted route.

Planned route: Linphone SIP account 1001 calls extension 2000 on Asterisk; ARI/ExternalMedia connects the existing voice session gateway. Tenant/assistant selection must come from trusted server-side extension configuration. Keep SIP/RTP private, ARI internal/authenticated and credentials outside source; enable negotiated SRTP where supported. Recording defaults to off. Exact host/network and accepted speech artifacts are required before deployment. No SIP registration or real call has been tested.
