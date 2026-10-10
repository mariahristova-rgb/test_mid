# Local model setup

The owner's existing GCS Qwen3-4B artifacts are verified and cached under .assistant-model-cache/original. Exact source/revision/license/checksums are in MODEL_MEMORY_REPORT and artifacts/qwen-gcs-audit. No alternate LLM was downloaded. Original files and GCS were not overwritten.

scripts/convert_qwen_cpu.py creates a separate BF16 GGUF and Q4_K_M copy using digest-pinned official llama.cpp tools. Actual Q4_K_M size is 2,497,280,800 bytes; SHA-256 is 9a91506f18e56bfa9389a939db1b36029daf8c49327b0eb0bc9e19d627b00e79. The model loaded successfully in the CPU server. Configure context 4096, threads 4, batch 128, microbatch 64, parallel 1, GPU layers 0 and supported Jinja/non-thinking mode. It remains a persistent process; no artifact download occurs during calls.

scripts/stage_qwen_volume.py verifies and copies only this derived GGUF into testmid-cpu-voice_qwen-cache, a persistent Linux volume with explicit project/repository ownership labels. A conflicting/unowned volume or different staged checksum is rejected. Serving mounts it read-only; the original host cache is untouched. start-local.ps1 verifies both the converted artifact and staged cache. This evaluates Windows bind-mount overhead rather than assuming a speedup. Stop preserves the volume and database.

Multilingual faster-whisper small revision 536b0662742c02347bc0e980a01041f333bce120 is cached and MIT-declared. Worker settings: CPU/int8, beam 1, one native worker, bounded generated tokens, short utterance chunks, VAD and known-language hints; initial unknown language may detect Bulgarian/English. Actual recognition results, including failures, are preserved.

eSpeak is the initial GPL-compatible formant baseline. Actual synthesis works, but Bulgarian recognition of its robotic output failed. A reviewed Apache-declared 38M Bulgarian/English neural candidate and MIT MioCodec are separately provisioned for evaluation. Checkpoints load with weights_only=True; codec paths are local and CPU libraries are explicit. No training or real-person voice cloning was performed. The reference is the publisher's generic generated sample. Neural voice acceptance and live integration are pending.
