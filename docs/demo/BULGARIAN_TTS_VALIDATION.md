# Bulgarian TTS validation — actual synthesis, listening pending

An actual local eSpeak NG 1.51+dfsg-10+deb12u2 worker was built from official Debian packages. It provides Bulgarian and a separate en-US voice on CPU. Engine/voice data uses GPL-3.0-or-later; it is a formant synthesizer, not a downloaded neural voice. Distribution requires the applicable GPL notices/source obligations. The neural Piper Dimitar candidate was not installed or declared commercially cleared because its Lessac fine-tuning lineage remains unresolved.

Actual synthetic WAV samples in artifacts/voice-audio:

| Locale/phrase | Rate | Audio duration | Batch synthesis |
|---|---:|---:|---:|
| Bulgarian greeting | 22050 Hz | 4.972 s | 52.60 ms |
| Bulgarian name/date/time confirmation | 22050 Hz | 8.269 s | 46.83 ms |
| English greeting | 22050 Hz | 4.191 s | 40.42 ms |
| English confirmation | 22050 Hz | 7.039 s | 66.74 ms |

These are actual local synthesis measurements with fictional text. First-audio latency was not measured in this initial batch test. They are not caller-audible/SIP measurements. Cyrillic produces real PCM audio, date/time normalization is applied, no English fallback occurs for Bulgarian, and output is converted to 8 kHz PCMU for telephony. Native synthesis has a timeout and one admitted request.

The Bulgarian greeting was shared for listening review. Human intelligibility/brand/name pronunciation and final demo acceptance remain pending; the voice is explicitly robotic. A nonempty WAV does not establish intelligibility. Peak worker RAM and recognition of the synthesized phrases will be measured separately.

## Neural candidate: actual CPU evaluation

[BgTTS-38M-V2](https://huggingface.co/beleata74/BgTTS-38M-V2) declares Apache-2.0 and Bulgarian/English support; pinned revision 3f6ca06b3ca78352eb00d8e96349c0bedaa3d2f1. Checkpoint: 38.2M parameters, 152,965,750 bytes. [MioCodec-25Hz-24kHz](https://huggingface.co/Aratako/MioCodec-25Hz-24kHz) declares MIT; revision 3a737f0de2c6324cb2fe40c1fbd1056c7add423d, codec weights 523,087,956 bytes. These declarations permit commercial use subject to their notices/terms; they do not warrant every training-data right. Official WavLM speech-feature weights are separately cached (377,604,347 bytes). No alternate LLM was downloaded.

Actual isolated network-disabled CPU synthesis generated 24 kHz WAVs: Bulgarian greeting 4.56 seconds audio / 9.776 seconds synthesis, request 4.44 / 5.743, name 1.56 / 2.088 and short confirmation 1.04 / 2.615. English request: 4.48 / 9.390 seconds. These are batch measurements, not first-audio or SIP-turn latency. Receipts and WAVs: artifacts/neural-voice-audio.

A generic publisher-generated reference is used; no identified person is targeted. Checkpoints load with weights_only=True; reviewed codec YAML and weights remain local. The adapter verifies cache digests before loading and releases unused encoder weights after warm reference extraction. Its first decoder-only test failed because decode needed encoder convolution geometry. A correction retains geometry separately; actual retest is required before deployment.

The corrected adapter subsequently passed offline synthesis of all six Bulgarian/English phrases. Preload including hash verification: 86.913 seconds. Bulgarian request/name/long confirmation synthesis: 12.144 / 2.223 / 6.575 seconds; English request/name/confirmation: 6.402 / 3.325 / 3.208 seconds. The longer Bulgarian confirmation still transcribed incorrectly as “да подтвържда вам чеса за прегляда.” English confirmation was “Yes, I confirmed the appointment.” Neither passes the current exact consent gate. Bulgarian request returned HTTP 504 after 29.051 seconds under build contention. Actual results are preserved in adapter-results.json and stt-adapter-results.json; do not replace these failures with the reference text.

Bandlimited 8 kHz synthesis and four-thread STT were subsequently measured. Updated Bulgarian request/name transcriptions were “Здравейте! Искам да запиша час за следващия понедельник в 15 часа.” and “Казом се Мария Демо.” The explicit weekday synonym preserves the actual Monday meaning; no arbitrary date guessing occurs. The shorter confirmation remained “Путвърждавам часа.” and is not accepted as consent. Earlier “Да, потвърждавам” was recognized as “Де потвърждавам,” also rejected. No spelling repair or dropped negation is used to force a booking. Listening review, representative human audio and three correct live journeys remain open. The publisher's advertised CPU RTF is not substituted for these measured results. [Microsoft's WavLM source license](https://raw.githubusercontent.com/microsoft/unilm/master/LICENSE) is MIT; notices for the feature encoder remain part of deployment review.

Telephone-band faster-whisper output improved to “Искам да запише час за следващия понеделник с 15 часа.” and “Казом се, Мария Демо.” Short consent was “Купърх да вам.” and failed the strict confirmation gate. It must not create an appointment. Longer clear consent phrases are undergoing actual adapter/ASR evaluation. Human listening and complete call acceptance remain open. Bulgarian TTS is not marked complete.

## Phase 8 measured outcome — 9 October 2026

**Bulgarian TTS acceptance remains incomplete.** Four mandatory output phrases and five recognition phrases were actually synthesized through the existing CPU BG38/MioCodec adapter. All waveforms and actual round-trip transcripts are retained in artifacts/phase8/speech-corpus; no expected text is substituted for an observed result. The telephone-band “петнадесет часа” and reservation confirmation are corrupted by STT. Nonempty audio is not human intelligibility evidence.

An evaluation of the already-installed Microsoft Ivan voice produced seven real 16 kHz PCM waveforms. Cold full synthesis was 360.973 ms; warmed full synthesis was approximately 13–22 ms. Evaluation-process working set was 104,607,744–108,703,744 bytes. These are host SDK evaluation measurements, not deployed-service or SIP measurements. Waveforms, timings and pronunciation checks are retained under artifacts/phase8/windows-voice. The original wideband clock was recognized as “Искам час в 15 часа.” in 12,116.36 ms; bandlimited telephone round-trip returned “Из към час, бъпет наися часа.” in 6,104.19 ms. Human listening remains pending.

[Microsoft documents Bulgarian Ivan](https://support.microsoft.com/en-us/accessibility/windows/narrator/appendix-a-supported-languages-and-voices). Installed Windows voices are proprietary Microsoft components, not Ontelyx semantic runtime components. No voice assets were downloaded or redistributed. Commercial deployment rights under applicable Windows terms have not been certified. A private authenticated local-demo bridge was proposed, but has not been activated: Phase 8 explicitly requires owner approval before major TTS replacement, and that answer remains pending. The current licensed-model declarations and existing worker are preserved.

**PARTIAL / BLOCKED.** Three real SIP attempts finished, but the booking release gate did not pass. Registration, call establishment and response packets are separate from caller-heard confirmation. Known locale was selected through the existing authenticated call-language control; no STT transcript was injected. Synthetic WAV callers were used, not representative human callers. Raw live transcripts remain disabled by the existing privacy settings.

| Locale | Attempt | Call ID | Last booking state | New confirmed bookings | Request/name/confirm observation ms |
|---|---|---|---|---|---|
| bg-BG | 20261009T100552Z-92117b | 7231118e-9424-4daa-a87a-3e3a46279cc4 | awaiting_confirmation | 0 | 33484/44953/68437 |
| en-US | 20261009T100926Z-58c039 | 1b8ef3fe-c435-46ec-94a3-a6b57cd11df5 | awaiting_confirmation | 0 | 26110/30734/73907 |
| bg-BG | 20261009T101251Z-931cd0 | 099194ab-20ff-44b1-90fd-a5afa9b292d6 | awaiting_confirmation | 0 | 29609/41047/68281 |

Each attempt retains its input hashes, received WAV, redacted signaling, resource samples, conversation, agent handoffs and tool results under artifacts/phase8/sip-tests/<attempt>/. The summary is artifacts/phase8/three-call-results.json. State observation timings include input playback, buffering, inference and polling; they are not synchronized first-audible latency. No new correct booking or three-call success is inferred. The prior correct English booking remains historical evidence, not a Phase 8 pass.

Required remaining gates: reliable telephone-band time/consent recognition, caller-heard intelligibility, real in-call language switching/unavailable/interruption/failure scenarios, visual dashboard verification and three consecutive complete correct bookings. Existing unit tests do not establish those live gates. Browser security policy rejected local dashboard inspection; no indirect or alternate-browser bypass was attempted.

## Phase 8B measured update — 9 October 2026

Development-only evaluation authorized by the Phase 8B request. Microsoft Ivan was found in installed Windows voices and generated nine real 16 kHz mono PCM16 WAVs through WinRT. No voice assets were downloaded, redistributed or installed. The harness records full-batch availability, process CPU time and working-set snapshots/OS process peak; these exclude CPU/memory in any separate Windows component. Full synthesis is not streaming first-audio or caller-heard latency.

| Phrase | Full synthesis ms | Process CPU ms | Working set bytes | Process peak working set bytes |
|---|---|---|---|---|
| Да | 184.840 | 203.125 | 106131456 | 114593792 |
| Да, потвърждавам | 19.982 | 15.625 | 107360256 | 114593792 |
| Потвърждавам часа | 11.242 | 15.625 | 107737088 | 114593792 |
| Точно така | 8.202 | 15.625 | 108027904 | 114593792 |
| Не, благодаря | 8.831 | 0.000 | 108519424 | 114593792 |
| Искам друг час | 9.173 | 15.625 | 108843008 | 114593792 |
| Може би | 7.345 | 0.000 | 108961792 | 114593792 |
| Не потвърждавам | 7.392 | 15.625 | 109273088 | 114593792 |
| Да, потвърждавам? | 10.686 | 15.625 | 110166016 | 114593792 |

The Windows-generated files were transferred into the repository-owned Docker STT container, converted to PCMU telephone audio and successfully transcribed for selected affirmative/request fixtures. SHA-256 hashes and waveforms are retained. The test process loads the current trusted backend VAD source without modifying the speech image. Initial fixture preparation failed on copied-directory permissions and an older image's VAD signature; only the temporary test directory/import was corrected. These failures did not execute booking tools.

The existing BG38/MioCodec response provider remains active. Its fourteen-case Phase 8 corpus took 1,764–13,819 ms full batch synthesis; the current Ivan trial is much faster but uses different phrases/processes and is not a controlled live-service comparison. The current response voice has actual SIP output; Ivan has only host evaluation/caller-fixture output. Human pronunciation/intelligibility remains an explicit listening gate.

[Microsoft's SpeechSynthesizer documentation](https://learn.microsoft.com/en-us/uwp/api/windows.media.speechsynthesis.speechsynthesizer?view=winrt-26100) describes use of installed Microsoft-signed voices. [Applicable Microsoft license terms](https://www.microsoft.com/en-us/useterms) depend on the installed product/license. This evaluation does not certify commercial hosting, redistribution or production rights. Installed Ivan is proprietary Microsoft speech, not an Ontelyx semantic runtime dependency. The owner authorized evaluation only; no production default or private live voice bridge was changed. Further production-default approval and licensing review are separate prerequisites.

Additional same-phrase comparison, actual warm current-provider API versus Windows batch SDK (different interfaces and processes, not a controlled service-capacity guarantee):

| Phrase | BG38 HTTP batch ms | Ivan batch ms | BG38 phone-band actual STT |
|---|---|---|---|
| Да | 1238.973 | 184.840 | Да. |
| Да, потвърждавам | 2519.100 | 19.982 | Де потвърждавам. |
| Потвърждавам часа | 2262.476 | 11.242 | Попърждавам часа. |
| Точно така | 1904.403 | 8.202 | Тоцнотък е? |
| Не, благодаря | 2944.538 | 8.831 | Не бъгдаря. |
| Искам друг час | 1884.905 | 9.173 | Искам друг час. |
| Може би | 1574.556 | 7.345 | Може би. |
| Не потвърждавам | 4765.458 | 7.392 | Не потвърждавам. |
| Да, потвърждавам? | 2725.718 | 10.686 | Де потвърждавам. |

All nine BG38 synthesis/recognition calls returned HTTP 200. Short “Да” was recognized correctly; longer affirmative and “Точно така” were corrupted and remain unapproved text. Negative and ambiguous controls never authorize booking in the exact gate. The original question control became corrupted/unclear, while the Ivan question control became affirmative. Neither a nonempty waveform nor selective correct recognition establishes general human intelligibility or speech-consent safety. Evidence: artifacts/phase8b/current-tts/results.json and actual WAVs.
