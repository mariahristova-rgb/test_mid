# Model and memory audit

Owner-supplied source: gs://ai_data_solutions/ontelyx/ai_model/Qwen3-4B/. Read-only access is verified. Configuration declares Qwen3ForCausalLM/qwen3, BF16, hidden size 2560, 36 layers, 32 attention heads, vocab size 151936, model context 40960 and no quantization. Tokenizer class Qwen2Tokenizer has an embedded tool/non-thinking chat template; its advertised 131072 tokenizer limit is not used to override the model's configured limit. Actual serving context is 4096.

All model/tokenizer download metadata matches original revision 1cfa9a7208912126459214e8b04321603b3df60c. The source license is Apache-2.0. Pinned object generations and local SHA-256 are recorded in artifacts/qwen-gcs-audit. The manifest SHA-256 is b4a33eb5ac14f51e35ce3bac2a4a77e2f0846f95859474a1c6e81aabcecac1ee. Every downloaded file passed verification before publishing the original cache.

Three original shard sizes: 3,957,900,840; 3,987,450,520; 99,630,640 bytes. Weight-index tensor data totals 8,044,936,192 bytes across 398 tensors. Verified cached artifact files total 8,060,925,056 bytes. Original storage remains unchanged; no alternate LLM or 8B fallback was fetched. Q4_K_M conversion is explicitly authorized by Phase 7D and writes a separate cache.

The original BF16 model alone exceeds the observed Docker memory allocation before inference/speech overhead. Actual converted BF16 GGUF: 8,051,285,280 bytes. Actual Q4_K_M: 2,497,280,800 bytes, SHA-256 9a91506f18e56bfa9389a939db1b36029daf8c49327b0eb0bc9e19d627b00e79. Original files were mounted read-only. CPU model loading succeeded. One observed runtime snapshot was Qwen 3.084 GiB / 4 GiB, STT 578.6 MiB / 1.172 GiB and TTS 41.16 MiB / 256 MiB. These are snapshots, not peak measurements.

Initial observed baseline: host available memory 2,363,112 KiB; C: free 72,270,745,600 bytes; D: free 42,891,137,024 bytes. Existing unrelated cruise_etl/cruise_backend containers showed 185 MiB/212.5 MiB and 202.47%/189.57% CPU in one sample (Docker 100% means one logical CPU). They were not stopped. This contention must be retained in benchmark context.

Actual cgroup v2 high-water marks after the first neural-worker serial attempts (startup included): Qwen 4,114,595,840 bytes; STT 744,280,064; neural TTS 1,820,364,800; backend 116,912,128; Asterisk 95,817,728; frontend 24,674,304. All recorded restart counts were zero and OOMKilled false. cgroup charged memory includes file cache/kernel memory; it differs from Docker's working-set display and Windows process RSS. Individual maxima need not occur simultaneously, so their sum is not a measured stack peak. Evidence: artifacts/local-demo/cgroup-before-timeout-fix.json. Final-run peaks are recorded separately after the updated configuration is exercised.

Later Linux-volume/four-thread-STT run: Qwen peak 4,294,971,392 bytes, STT 832,241,664, TTS 1,907,376,128, backend 145,833,984, Asterisk 116,822,016 and frontend 24,973,312. Restart/OOMKilled counters remained zero/false. Qwen recorded 6,166 memory-max events with zero OOM kills: its 4 GiB cap experienced pressure despite successful loading. This is a material reliability/performance limitation, not proof of memory headroom. Evidence: artifacts/local-demo/cgroup-after-final-calls.json. A displayed steady snapshot was Qwen 3.224 GiB, STT 354.5 MiB and TTS 1.364 GiB. All limits/peaks must be read with current 7.44 GiB WSL allocation and unrelated workloads retained.

Final repeat-run cgroup peaks: Qwen 4,294,971,392 bytes, STT 914,743,296, TTS 1,907,376,128, backend 117,669,888, Asterisk 116,822,016 and frontend 24,973,312. All restart counts zero / OOMKilled false. Backend was replaced between increments, so its peak starts at its own latest startup. Evidence: artifacts/local-demo/cgroup-final-results.json. CPU percent samples are captured in each attempt's resources.json; 100% represents one logical CPU, and these interval samples are not continuous CPU peaks.

Final three-call interval CPU observations (100% = one logical CPU; not continuous peaks):

| Owned service | Samples | Mean CPU % | Maximum sampled CPU % |
|---|---:|---:|---:|
| testmid-cpu-voice-qwen-1 | 154 | 112.01 | 427.69 |
| testmid-cpu-voice-stt-1 | 154 | 83.62 | 418.91 |
| testmid-cpu-voice-tts-1 | 154 | 53.49 | 214.41 |
| testmid-cpu-voice-backend-1 | 154 | 17.16 | 108.31 |
| testmid-cpu-voice-asterisk-1 | 154 | 6.17 | 14.14 |
