# Phase15 UX acceptance

11 October 2026. Local feature branch `codex/phase15-product-experience`; no Phase 15 push/merge/public deployment. Existing URLs and the two-agent runtime are retained.


Backend final:300 tests pass in116.061s. Frontend tests:25 pass (22 baseline +3 navigation); targeted InboxQueue tests cover tenant/role isolation, revision conflicts, default note redaction, audited reveal, bounded expiry purge and no automatic AI takeover. Full suite includes Google mock lifecycle and existing session/origin/security scenarios. Source boundary:216 files, zero failures.

Initial frontend lint had29 format warnings; corrected with targeted ESLint --fix and rerun. Browser acceptance attempt for the clearly labeled synthetic tenant was rejected by automatic review due established browser/CUA restriction. No rawCDP/alternative-browser/shell screenshot workaround. Explicit scoped owner approval has been requested. Until a successful browser check, navigation, Inbox controls, mobile widths, keyboard/screen-reader, offline/reconnect and publish/unpublish are IMPLEMENTED_UNVERIFIED.

Synthetic tenant1204079a-92e4-48cd-bd58-3c0b21723cd4 and conversatione41ab62a-f06c-4a2b-acf6-8a6e14d3dcbe are isolated fixtures, not real traffic. UI route link uses an authorized tenant hint; server membership still validates it. Named real Google receipts are recorded separately in SMART_APPOINTMENT_MANAGER.md.

Physical iOS Safari/Android Chrome, 200% zoom, screen-reader announcements, slow-network Web Vitals, widget-origin staging and actual reminder delivery remain open. No complete WCAG or production-ready claim.


## Superseding synthetic browser observations

Owner explicitly approved local synthetic browser automation/screenshots after the initial rejection. The subsequent approved check passed: assign to self → awaiting customer; create staff note → audited reveal; takeover pauses AI → local operator reply persists. No real conversation was inspected. Widths320/360/375/390/430/768/1024/1440 had document scrollWidth==clientWidth. Separate fresh screenshots are needed after viewport changes because rapid batched captures initially returned stale painted frames. Correct320 capture shows no clipping but excessive filter height; filters are now collapsed by default in source. Final-build recheck pending.

Browser-observed provenance bug: outbound operator reply was labelled Assistant. Metadata is now kind=human/agent=human, and messageSpeaker() limits the human label to outbound messages; incoming spoofed metadata cannot impersonate staff. Action chooser previously offered unsupported Concierge forms; inboxToolNames() now requires assistant permission plus an implemented argument form. These fixes have regression tests. Old messages without provenance are not retrospectively relabelled.

Language switch to Bulgarian localized controls; proper names and synthetic freely entered text are not translated. A shared open action/status translation was ambiguous in Bulgarian; status_open is now separate. Source includes compact filters and actual tenant name rather than an opaque UUID.

Local opt-in web-vitals sample: LCP1412ms, CLS0, INP480ms, desktop1280x720, unthrottled Windows Chromium, sample size1. This is a private login/Inbox session, not representative p75. INP misses the200ms target; no performance victory is claimed. Metrics contain numeric values/viewport only, no attribution, URL, transcript or outbound telemetry. Production Google builds exclude the local-only hook.


Final local checkpoint:309 backend tests/86.112s,29 frontend tests,227-file boundary check/no failures and no-leak source scan. Browser final390px verified compact filter disclosure, human sender label and resume. Native ctrl+plus did not change the effective viewport;200%zoom remains unverified. Second mixed-resize sampleLCP1832ms,CLS0,INP992ms is not a matched performance improvement. No real-device/screen-reader/offline or hosted identity acceptance is asserted.
