# Phase 8B confirmation recovery

Status: investigation and regression verification in progress. No new live acceptance is claimed.

Phase 8's three calls reached exact pending proposals but remained awaiting confirmation. Privacy settings correctly omitted raw live transcripts, so their exact ASR words cannot be reconstructed. The separately retained synthetic corpus produced corrupted Bulgarian consent and English past-tense consent. These are observed acoustic failures, not reconstructed live transcripts.

Code inspection identifies an additional deterministic boundary: even an exact literal affirmative was vetoed unless Qwen independently returned confirm. The targeted fix uses an exact, context-aware decision only for an existing, unexpired pending proposal; ambiguous text still does not authorize tools. Explicit rejection and requested replacement invalidate the old approval. The executor and existing approval path still recheck permissions, fingerprint, expiry, availability and idempotency. A completed booking reuses its prior result for duplicate literal confirmation.

The existing content-free Operations collector now holds at most 256 trace entries per tenant. Stages share a call/utterance-derived correlation ID: audio received, VAD final, STT partial support, STT final presence, locale selected, pending state, confirmation decision, authorized agent, tool completion, persisted appointment, TTS completion and first outbound packet. No raw transcript, customer name, model arguments or audio is logged. The local Whisper worker is final-only; partial_supported=false is recorded instead of inventing partial hypotheses. Outbound packet delivery is not proof that a human heard or understood audio.

Session close cancels an outstanding pending approval after in-flight work settles; completed bookings remain. Playback, handoff and short silence do not clear context. Explicit switching preserves the proposal and changes the response locale. Web Chat retains its existing HTTP 409 expiry contract.

Seven new deterministic tests cover durable one-time execution and replay, rejection, ambiguity/questions, expiry, slot replacement, locale retention and tenant-scoped bounded trace privacy. Their first run passed; one existing web expiry contract exposed a regression, which was corrected and retested. Full regressions and telephone-band benchmarks follow before live testing. The owner confirmed availability for live acceptance; no TTS default change is authorized or made.

## Phase 8B measured update — 9 October 2026

The new trace is bounded in-memory operational metadata; it is exported to each actual synthetic attempt receipt. It contains no raw customer text/audio. Correlation IDs join audio receipt/VAD/STT/locale/state/decision/agent/tool/persistence/TTS/output. Approval parent correlation is retained. Outbound packet timestamps measure delivery to the caller transport, not subjective hearing. Local partial recognition is unsupported and never fabricated.

The initial live image emitted appointment_persisted after the insert inside the transaction; each claimed live booking was independently verified through the authoritative API after commit. A follow-up instrumentation correction uses the existing after-transaction hook and verifies the committed approval/appointment before emitting this stage, so a rollback never generates a persistence claim. The new rollback regression passes. This correction does not change booking behavior or model services; its deployment/version is recorded separately from earlier receipts.

Exact current failing acoustic boundary: telephone-band ASR loses or changes some confirmation words and question punctuation, before deterministic state-aware evaluation. An additional code-level model-veto boundary was removed for literal pending consent. A successful selected affirmative does not erase negative/control failures.

**PARTIAL / BLOCKED.** Deterministic confirmation is recovered; complete live acceptance is not inferred. The owner declared availability for live acceptance before new SIP attempts. Caller fixtures combine existing BG38 speech and authorized Ivan evaluation speech; the assistant's response provider remains BG38. Known locale is selected through the existing authenticated control, without transcript injection.

| Locale | Attempt | Call ID | Business workflow | Booking IDs | Human-heard verification |
|---|---|---|---|---|---|
| bg-BG | 20261009T105422Z-29fa08 | 38d1e640-f178-4b59-a901-021bbd8103e8 | True | e1918d21-a585-4b07-85dc-2947b037c450 | pending |
| en-US | 20261009T105839Z-e5d106 | 8c3cb1f5-ab9e-4853-890a-6180ed1a0e11 | True | 4c04be6e-27f1-4925-9737-3f6c7ff79a91 | pending |
| bg-BG | 20261009T110159Z-7f0d1a | 33c8e022-7c76-4ad2-a4c6-765caebd2c62 | True | f170806c-a94b-4c58-9379-cae95c27e9e2 | pending |

Three consecutive complete calls, human-audible correct confirmation, visual dashboard evidence and the acoustic question false-positive control remain open gates. Received RTP/nonzero WAV/persisted row alone cannot satisfy human acceptance. New receipts are artifacts/phase8b/sip-tests/<attempt>/; prior unsuccessful attempts remain in Phase 8 evidence. Sequence continuation is permitted only after the preceding business journey passes; no failure is silently omitted. Browser policy previously blocked local inspection and is not bypassed; the owner can verify the dashboard directly.

All three consecutive selected-affirmative SIP business journeys passed. Each created one distinct correct appointment, and response audio reached the caller transport. All three survived the targeted backend restart; no active API calls or Asterisk channels remain. Caller-side final-45-second excerpts were provided for human listening. This is business/transport evidence, not full human acceptance.

The owner initially reported ERR_CONNECTION_REFUSED when checking the dashboard. The intended URL is http://127.0.0.1:3011/dashboard; the existing listener was verified on 127.0.0.1:3011 and returned HTTP 200. Visual booking verification remains pending the owner’s follow-up; HTTP availability is not visual proof.
