

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
