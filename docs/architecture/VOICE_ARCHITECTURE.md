# Phase 3 voice architecture

Status: **mock integration ready; live telephone/speech functionality unverified**. Phase 2 was inspected and its 72 retained tests passed before the increment. The same assistant configuration, tenant membership, conversations, receptionist/executor, tool registry, booking approvals and calendar are reused. `VoiceRuntime` is a media supervisor, not another AI agent runtime.

```mermaid
flowchart LR
  Call[Signed incoming call] --> Gateway[Tenant + number routing]
  Gateway --> Session[Persisted CallSession]
  Session --> Ticket[One-use stream ticket]
  Ticket --> Reader[Async audio reader / bounded buffer]
  Reader --> VAD[Turn detection / final settling]
  VAD --> Queue[Bounded turn queue]
  Queue --> Worker[Dedicated worker pool]
  Worker --> STT[STT provider]
  STT --> Agents[Existing receptionist + executor]
  Agents --> Tools[Authorized tools / approval / calendar]
  Tools --> TTS[TTS provider]
  TTS --> Output[Paced audio / clear on interruption]
  Output --> Caller[Caller]
```

## Modules and contracts

| File | Responsibility |
|---|---|
| `domain.py` | TelephonyProvider, AudioTransport, STT/TTS ports, typed AudioFrame/RecognitionResult and tenant-owned VoiceConfig |
| `voice.py` | VoiceSessionManager: call creation/lifecycle, same orchestrator invocation, final-turn idempotency, language/transfer/consent, usage/retention |
| `voice_gateway.py` | Signed incoming routing, encrypted tenant credentials, current service membership, immutable call binding and one-use tickets |
| `voice_stream.py` | Async WebSocket reader, bounded turn queue, independent worker pool, playback interruption, deadlines and cleanup |
| `audio.py` | Bounded turn buffer, RMS/silence turn detection, G.711 mu-law conversion and telephony PCM conversion |
| `live_voice.py` | Disabled-by-default Twilio control/TwiML and Azure short-utterance STT/TTS HTTP adapters; SDK/HTTP details stay in infrastructure |
| `api.py` / frontend Calls | Authenticated mock sessions, stream-ticket issuance, signed provider webhook, WebSocket endpoint, bilingual configuration and synthetic media controls |

Twilio/PBX/carrier owns SIP signaling, registration and media negotiation. The application does not implement SIP. The installed integration handles routed E.164 telephone numbers and bidirectional media; direct SIP-URI routing/INVITE handling is not implemented. Another SIP gateway can implement the same provider/transport contracts without replacing either agent.

## Audio and concurrency

`/voice/media` consumes a one-use 60-second ticket in its first message, never in a query string. Twilio sends it as a Stream custom parameter. The ticket binds tenant, call, current service user and provider mode; changed call IDs, revoked users, disabled assistants, expired/reused tickets and simultaneous streams are rejected. Twilio start metadata and signed WebSocket handshake are also checked. Mock browser Origin is restricted. Handshakes reuse the existing IP limiter, and a stream has a 200-packet/second ceiling.

The reader validates frame size, sequence and codec, handles `clear`/ping/stop, buffers a bounded utterance and queues it. It never performs STT, LLM or tool work. Queue capacity is four turns; buffer duration is configurable, with a 30-second maximum. PCM/mu-law activity uses a simple energy threshold and configured silence duration. Fixture UTF-8 frames explicitly mark turn completion; they are not sound or recognition samples. This is basic VAD, not a noise/echo-trained detector or adaptive jitter buffer.

Four worker threads process speech/agent/tool operations outside the audio loop. Final hypotheses settle for 100ms; partial recognition never invokes tools. Completed utterance IDs are frozen so subsequent duplicate/corrected finals cannot repeat an action. Pending corrections replace the hypothesis before processing. The application-owned explicit affirmation gate still protects booking; a model classification cannot grant permission.

Barge-in increments a playback generation and clears buffered output immediately. Stale TTS/result playback is suppressed while business outcomes remain persisted. Turn latency bounds queue/processing/TTS time to first audio; playback itself is paced separately. Call-duration and silence limits close streams and persist terminal usage; a maintenance task expires calls that never attach. Provider failure never causes an automatic business-action retry.

A running synchronous worker cannot be forcibly killed safely. A valid action already in its transaction may complete after an interruption/timeout; cleanup follows without reopening the call or retrying it. Hard cancellation, distributed workers/outbox and live latency/echo assessment remain production gates. SQLite serializes domain writes, so this is a single-process foundation, not a validated high-concurrency carrier service.

## Persistence and privacy

Forward migration v3 adds tenant-owned CallEvent, CallParticipant, CallUsage, stream-ticket, encrypted-transcript metadata and recording-excerpt metadata tables. Composite conversation ownership is enforced; call IDs are linked inside payloads. Legacy session lifecycle fields receive additive defaults without deleting stored data/transcripts. Earlier legacy plaintext transcript disposition stays owner-managed.

CallSession stores tenant/assistant/conversation, provider call ID, masked caller, status, start/end/duration, active locale, owner/connection, last activity and safe error code. Agent/tool execution references use the existing conversation relationship. Events/audit contain action/status/locale/correlation identifiers, not raw audio or request bodies. Usage records contain duration and null price; no live billing rate is invented.

Recording/transcripts default off. New opt-in requires tenant allowance, assistant policy, configured basis/notice, explicit caller consent and a configured encryption key. Transcript text and completed audio excerpts are stored encrypted, with expiry bounded by assistant and tenant retention. This is excerpt storage, not a continuous stereo carrier recording. Voice conversation message bodies are redacted before commit; business records such as appointment name/time are still retained for their operational purpose. Temporary active-call response text is cleared at termination. Administrator-only transcript reads enforce expiry; an explicit retention endpoint redacts expired encrypted content.

Configuration notices and basis fields are technical controls, not legal approval or GDPR certification. Real deployment needs lawful notice/consent design, key rotation, full operational-data retention/export/deletion, encrypted volumes and access review.

## Demonstration and verification

[VOICE_DEMO.json](VOICE_DEMO.json) is produced by `scripts/demo_voice.py`: signed mock incoming call → authenticated WebSocket → fixture audio → STT mock → both existing agents/tools → TTS fixture → caller. Bulgarian/English greetings and three-turn booking complete using Europe/Sofia and a fixed fictional timestamp. Each language uses an independent in-memory calendar; no real call/audio/provider account is used.

Tests include signatures/routing, lifecycle/usage, both locales, partial/final correction duplicates, language switching, transfer/decline, permission and tenant denial, ciphertext/consent/retention, forward migration and reopen, frame/VAD limits, provider errors, latency/silence/orphan timeouts and responsive ping/clear during slow agent execution. Current observed counts are in IMPLEMENTATION_STATUS.

Observed final results: 99 backend tests (72 retained + 27 voice), 7 UI/security tests, typecheck, zero-warning lint, frontend build, browser streamed-booking/call/mobile checks and dependency/import checks passed. The staged-source Gitleaks scan passed after a synthetic signing fixture was changed to generated per-test material. No real provider, microphone sample or telephone call was used in these results.
