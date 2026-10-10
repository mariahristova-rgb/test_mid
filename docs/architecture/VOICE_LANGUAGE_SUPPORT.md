# Voice language support and evidence

The configuration and mock pipeline require bg-BG and en-US. **Neither language has been evaluated with real speech in this application.** `speech_validated` remains false and live adapters are labeled LIVE_UNVERIFIED.

| Layer | bg-BG / en-US evidence | Readiness |
|---|---|---|
| Configuration, greetings/notices, voice IDs | Typed bilingual maps; incompatible voices rejected; tenant/assistant-specific settings | Tested |
| Mock STT/TTS | UTF-8 fixture decode/encode preserves Cyrillic, names, addresses and phone text | Tested simulation; not sound/recognition |
| Shared agents and booking | Final recognition → same language resolver/handoff/tools; localized details/consent/confirmation | Tested both languages |
| Language switching | Explicit API/recognized commands preserve locale in conversation and subsequent handoffs; ambiguous text does not switch | Tested mock |
| Azure STT/TTS metadata | Official locale table lists Bulgarian/English and Bulgarian Kalina/Borislav voices | Documented availability, not application verification |
| Actual speech, pronunciation, telephone audio, latency | No credentials/sample audio/authorized real calls supplied | NOT RUN |

Microsoft's [language support table](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=stt) lists bg-BG recognition and `bg-BG-KalinaNeural` / `bg-BG-BorislavNeural` synthesis. The adapter also includes `en-US-JennyNeural` and `en-US-GuyNeural`. This metadata selects candidates; it does not establish quality, account/region availability or this integration's working Bulgarian coverage.

Default synthetic voices are `mock-bg` and `mock-en`. For gated Azure evaluation, configure explicit locale-matching IDs; a missing/unsupported Bulgarian configuration is rejected, never silently replaced with English. Only voice infrastructure changes when providers change—the LLM and two agent roles remain independent.

The initial greeting uses the assistant's voice locale or an explicit caller/session choice. In mock mode, reliable recognized-content detection can establish the language on the first turn. Once established, it persists until an explicit change. Commands include `Премини на английски`, `Премини на български`, `switch to English` and `switch to Bulgarian`; supported commands do not translate technical IDs/tool keys.

Azure REST recognition is configured for one language per utterance and [returns final results only](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-speech-to-text-short). It does not perform acoustic auto-identification in this adapter. For real callers, choose a known language/number routing or implement and evaluate language selection/identification before relying on automatic behavior. Mock text detection is not evidence of detecting spoken Bulgarian/English audio.

Dates use the persisted conversation message timestamp and explicit tenant timezone, default Europe/Sofia. UI, conversation and voice locale remain separate. Synthetic tests cover booking tomorrow at 15:00, names/details and confirmation; phone IDs use E.164 and protected display. The pipeline preserves Unicode, while actual pronunciation of Bulgarian names/addresses/phone numbers, spoken-number normalization and acoustic recognition of dates must still be assessed.

## Authorized real evaluation gate

After explicit test-account/number authorization and secure configuration, record consented/synthetic test samples for both languages: greeting, common names, street addresses, +359 telephone numbers, weekdays/relative dates, durations, confirmation/decline, language change and human escalation. Include quiet/noisy telephone-bandwidth input, interruptions, corrections/repeated finals and failed transfers. Measure transcription correctness, unintended tool execution, TTS intelligibility, time-to-first-audio and transfer/disconnect outcomes; preserve event/correlation IDs without credentials or unnecessary raw personal data.

Document actual account/region/voice IDs, sample corpus, results and limitations. Do not set a verified flag or declare production readiness merely because documentation lists bg-BG or mock/HTTP contract tests pass.
