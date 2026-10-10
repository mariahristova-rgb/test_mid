# Local voice acceptance procedure and current result

1. Start only the scoped project and verify all health checks, Qwen loading and ARI application registration.
2. Register Windows account 1001, dial 2000, verify real two-way RTP and greeting. Compare actual CallSession/provider/status and cleanup.
3. Speak a fictional Bulgarian booking request for a real available next-Monday slot, supply a fictional name, listen to the concrete proposal and explicitly confirm. Verify the persisted booking identifier and tool/agent activity in the dashboard. Repeat in English.
4. Test locale switching, an actually occupied slot, duplicate confirmation, barge-in, provider timeout and disconnect. No success may be announced before persistence.
5. Complete three consecutive actual booking journeys and record timestamp, locale, transcript accuracy, booking ID, latency, resource peaks and errors. Health, signaling, synthetic API contracts and WAV existence are not substitutes.

Actual findings: Windows registration/call establishment and non-silent RTP greeting are observed. Original Qwen conversion/loading and bilingual intent/native-tool protocol tests are observed. Initial Qwen date/time/duration suggestions were wrong; explicit-entity schema grounding corrected the tested requests. Compact CPU mode classifies intent and uses request-scoped, authorization-bound tool argument references to reduce output tokens; registry validation/confirmation still controls execution.

Bulgarian robotic-source ASR failed; neural-source ASR improved but short confirmations still failed. These failures were not replaced with expected text. Three consecutive booking calls are NOT achieved. The task remains incomplete until recognition/voice/latency and full journeys pass.

Current measured result: one correct-details English SIP workflow persisted Jane Smith's booking (17b331e6-fda5-4735-8f88-1fd45d0e7b31). Final Bulgarian proposals matched date/time/name, but confirmation did not complete. Per-attempt audio/data/latency/resource reports are retained. Run scripts/prepare_call_audio.py inside the owned backend to generate caller fixtures, then scripts/test_cpu_voice_calls.py on Windows; the harness uses actual SIP audio and verifies proposals before consent. It does not inject recognition text or mark human-heard confirmation verified. Dashboard visual inspection was blocked by browser policy and needs human verification. Final services remain running for review; stop only them using scripts/demo/stop-local.ps1.
