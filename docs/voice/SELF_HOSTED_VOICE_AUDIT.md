# Phase 6C model, hardware and speech audit

Scope: `test_mid` only. The original repository is neither accessed nor modified. Baseline: Phase 5 has 168 passing backend tests and independent agent/tool/voice/tenant infrastructure. Its speech/LLM demonstration is synthetic; gated managed adapters are not used for this self-hosted demo.

## Existing artifacts and infrastructure

Repository source, model/config/manifests and public model-related keys in local environment files were inspected. No Qwen weights, GGUF/Safetensors files, tokenizer manifest, Qwen adapter, GCS bucket/prefix/version or inference endpoint was found. Removed-file evidence mentions the earlier GCS connector, but removed proprietary dependencies will not be restored. Google Cloud SDK executables are installed; that is not evidence of the correct project/bucket or artifact access.

The exact existing `gs://` location/version or authenticated endpoint has been requested. No bucket/path is invented, no cloud-wide enumeration is performed, and no alternative LLM is downloaded. Qwen3-4B is the default requested model; Qwen3-8B remains optional, never an automatic latency fallback.

## Observed local hardware

- CPU: AMD Ryzen 7 5700U, 8 physical / 16 logical cores.
- Host RAM: 16,483,885,056 bytes (approximately 15.35 GiB).
- GPU: AMD Radeon integrated graphics; WMI reports 536,870,912 bytes dedicated adapter memory. This is not a measurement of usable inference VRAM/shared GPU memory. No NVIDIA/CUDA runtime was detected in the executable audit.
- Docker: 16 CPUs, 7,984,476,160 bytes memory (approximately 7.44 GiB).
- C: free space observed approximately 72.3 GB. Model/cache requirements cannot be finalized without actual files/format/quantization.

Local CPU GGUF/llama.cpp is a candidate only if the existing artifact is compatible. vLLM requires compatible artifacts and a suitable supported GPU/runtime; this host's integrated GPU is not treated as a verified CUDA deployment. An existing authenticated Qwen endpoint takes precedence over another deployment. No automatic conversion or hardware performance claim is made.

## Bulgarian TTS feasibility — early blocker

No Bulgarian/English TTS artifacts are installed or configured. The current upstream Piper catalog includes `bg_BG-dimitar-medium`. Its model card describes CC0 training data and fine-tuning from US lessac; the Lessac dataset license excludes commercial use. This lineage requires clarification before commercial acceptance; the CC0 dataset declaration alone does not resolve it. The deployed artifact and pronunciation remain unverified. Piper engine licensing and each voice's license must be reviewed independently. Only small text metadata was fetched, with no voice weights downloaded.

eSpeak NG officially lists Bulgarian and English and is a possible local baseline, but its intelligibility/pronunciation is not assumed to meet the demo. A real Cyrillic/dental/name/date/number listening test and licensing record are required before marking TTS ready. Bulgarian will never fall back silently to an English voice. This blocker was reported before any new telephony feature work.

## Incremental plan

1. Add a read-only, checksum/version-verified GCS/cache contract with no registry fallback; provide explicit missing-configuration diagnostics.
2. Reuse the neutral LLM port for one tenant/assistant-routed Qwen endpoint, bounded structured output/tools, non-thinking hints, hidden-reasoning filtering, streaming/cancellation and usage measurements.
3. Evaluate local speech candidates with real audio and record actual results; gate unsupported/unverified Bulgarian voices.
4. Extend the existing voice/session infrastructure with Asterisk/PJSIP and bounded RTP/ExternalMedia processing, preserving the tool-confirmation and tenant boundaries.
5. Seed synthetic SmileCare configuration, test bilingual workflows, then perform real softphone and actual-model tests when the missing artifacts/host/voice are supplied.

## Readiness gates

Artifact format/provenance/license, exact serving backend and resource fit, actual Qwen Bulgarian/tool behavior, accepted BG/EN speech, SIP registration/calls and real end-to-end latency are unverified. Existing mock timings are not reused as real inference/speech measurements. No live demo readiness or production readiness is claimed.

Primary references: [Qwen3-4B license](https://huggingface.co/Qwen/Qwen3-4B/blob/main/LICENSE), [Qwen tool/non-thinking serving](https://github.com/QwenLM/Qwen3/blob/main/docs/source/framework/function_call.md), [Piper voices and per-voice licenses](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md), [eSpeak languages](https://github.com/espeak-ng/espeak-ng/blob/master/docs/languages.md).
