# Phase21 voice compatibility and licensing review

Primary sources checked13October2026. This is a candidate audit, not blanket commercial/distribution clearance or a model download. Verify exact pinned revisions/dependencies/notices before any execution/redistribution. No human reference audio/voice cloning authorized.

| Component | Candidate / source | License/support evidence | Decision |
|---|---|---|---|
| LLM | [Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B),[llama.cpp](https://github.com/ggml-org/llama.cpp) | Model Apache-2.0 declaration, runtimeMIT; current separateQ4_K_M/cache and CPU config already documented | Reuse existing; no alternate model/download; actual latency/quality gate open |
| VAD | [Silero](https://github.com/snakers4/silero-vad) | MIT,8/16kHz,PyTorch/ONNX; avoid new heavy runtime | Reuse existing STT VAD/turn segmentation first; no new install |
| VAD alternative | [py-webrtcvad license](https://github.com/wiseman/py-webrtcvad/blob/master/LICENSE) | Wrapper/WebRTC notice terms both need retention; frame/rate constraints must be checked | Optional later comparison, not selected/installed |
| ASR | [Whisper](https://github.com/openai/whisper),[faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Whisper code/weights MIT; faster-whisperMIT; multilingual small CPU/int8 already configured | Reuse cached small,beam1,one worker,bg/en hints; chunked final recognition is not native streaming |
| Neural TTS | [BG38](https://huggingface.co/beleata74/BgTTS-38M-V2),[MioCodec](https://huggingface.co/Aratako/MioCodec-25Hz-24kHz) | BG/EN model declaration Apache-2.0; codecMIT; torch/WavLM/reference dependencies require exact review | Existing adapter/cache reported; conditional evaluation only with permitted generic reference and dependency notices; no customer/unauthorized voice cloning |
| Formant TTS | [eSpeak NG](https://github.com/espeak-ng/espeak-ng) | GPL-3.0-or-later engine; existing BG/en-US synthetic synthesis evidence | Existing non-cloning fallback; notices/source obligations and robotic listening acceptance remain |
| Piper | [OHF Piper](https://github.com/OHF-Voice/piper1-gpl) | Current engineGPL; voices/datasets individually licensed | No blanket BG support/license claim; prior Dimitar lineage question unresolved |
| Kokoro | [Kokoro82M](https://huggingface.co/hexgrad/Kokoro-82M) | Apache-licensed weights/multilingual declaration; no verified BG voice in this audit | Not a BG replacement; no download/new runtime |
| XTTS | [XTTS-v2](https://huggingface.co/coqui/XTTS-v2) | CPML,not permissive-license equivalence; cloning-based examples | Not selected/commercially cleared; exact code/model restrictions require separate review |

BG38 card advertises CPU synthesis and BG/EN but publisher benchmark is not an Ontelyx benchmark. Standalone LICENSE URL could not be read in this audit; declaration alone is not complete code/dependency/training-rights clearance. Do not use its reference cloning functionality on a person's recording. Prefer preserved generic/formant synthetic reference only if reviewed; otherwise block that candidate.

Historical docs/demo/BULGARIAN_TTS_VALIDATION.md contains actual formant and neural WAV synthesis numbers and dependency revisions. Those are dated component/batch observations, not current first-audio/caller-intelligibility acceptance. Current containers stopped; Phase21ASR WER/RTF,first audio,end-to-end latency and listening are NOT_TESTED. No CUDA inferred from integrated graphics. No mandatory paid speech/LLM provider is introduced; hardware/electricity/storage still have costs.
