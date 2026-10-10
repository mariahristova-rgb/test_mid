# Local CPU demo readiness — incomplete

| Component | Actual status |
|---|---|
| Windows/WSL2/Linux Docker | VERIFIED_WORKING diagnostics |
| Original GCS model/cache | VERIFIED_WORKING download/hash checks |
| Q4_K_M conversion and CPU loading | VERIFIED_WORKING |
| Bulgarian/English model protocol | Tested; initial entity failure corrected with explicit grounding |
| Core agents/tools/persistence/isolation | 204 backend tests pass; correct-details English SIP business workflow verified |
| Asterisk/PJSIP Windows signaling | VERIFIED_WORKING registration/call establishment |
| RTP greeting | Non-silent audio observed after SDP correction |
| Multilingual small STT | Real inference works; Bulgarian confirmation/quality remains insufficient in tested synthetic samples |
| Formant TTS | Actual synthesis works; recognition/quality failed |
| Neural BG/EN candidate | Actual offline/HTTP synthesis and first-audio-body timing verified; human intelligibility/representative speech pending |
| Frontend/dashboard | Build/typecheck/lint/9 tests pass; actual booking API persists; visual inspection blocked by browser security policy |
| Three consecutive booking journeys | NOT_ACHIEVED |

No demo or production readiness is claimed. Missing acceptance evidence is recorded rather than hidden behind fabricated traces or provider responses. WSL's requested 10 GB target was not applied; actual Docker allocation remains 7.44 GiB. Native speech/model latency exceeds the conversational targets in several tests.

Verified English booking: 17b331e6-fda5-4735-8f88-1fd45d0e7b31, Jane Smith, 2026-10-12 15:00 Europe/Sofia, 30 minutes. Actual caller audio was transmitted through Windows PJSUA/Asterisk; all three business states and response packets were observed. The received WAV is real transport evidence, not a claim that a human heard intelligible confirmation. Earlier Jane Deemle booking failed name validation and was cancelled through an authorized tool, with original data/audit retained.

Bulgarian now reaches a correct-date/name proposal after exact weekday-synonym and safe name-prefix handling. Its tested confirmation remains insufficient; no corrupted consent spelling is repaired into approval. Correct-details English completion does not satisfy three consecutive bilingual journeys. Source check: 152 files / zero failures; staged redacted Gitleaks scan: 235 files / zero findings after removing the preview fixture token. Full suite: 204 tests / 67.426 seconds. Browser policy rejected the local dashboard URL, reporting a disallowed protocol despite its HTTP URL; no alternate browser or indirect UI workaround was attempted. Human visual verification was requested separately.

Actual restart persistence passed: the confirmed Jane Smith booking, ended SIP call, four agent rows and three tool rows remained after replacing/restarting the backend process. Evidence: artifacts/local-demo/restart-persistence-results.json. Final services remain running for review, with no active test calls or audio queue entries. This does not mark speech or production readiness complete.
