# Memory optimization — Phase 8

Current measured host: Ryzen 7 5700U, eight physical/sixteen logical cores; visible RAM 16,097,544 KiB. Available physical RAM was only 425,156 KiB; available virtual memory 6,944,328 KiB. C: free 33,397,481,472 bytes; D: free 42,891,137,024. Windows/background workloads remain part of this measurement. No unrelated process/container is stopped and no WSL allocation is increased.

Measured per-service swap: Qwen 48,975,872 bytes; STT 29,843,456; TTS 79,388,672 at the sampled instant. These are current values, not swap peaks. Current cgroup data is saved in artifacts/phase8/memory-current.json; historical memory-max pressure and limits are retained in MODEL_MEMORY_REPORT.

The existing single Qwen process, one STT worker, one TTS worker and one simultaneous demo call remain. Bounded VAD pre-roll adds at most 500 ms of PCM, within the existing utterance limit. No duplicate inference process or 8B model is introduced.

Installed Windows Ivan offline evaluation used roughly 104–109 MB working set and 13–361 ms total synthesis for seven phrases. This is an evaluation-process snapshot, not a deployed host-service peak. The current BG38/MioCodec worker uses substantially more memory and seconds of batch latency. Replacement is pending owner approval and licensing/deployment review; no live bridge is activated.

The measured 16 GB environment has limited headroom. Smallest candidates are freeing speech-model memory with an approved installed-voice bridge, then benchmarking narrowband ASR or a negotiated wideband path. Neither a memory increase nor a different model is presumed sufficient. Production capacity is unverified.

## Phase 8 measured outcome — 9 October 2026

Final cgroup measurements include startup/cache/kernel and have different service lifetimes. Individual peaks are not a simultaneous aggregate RAM peak. No sampled service had an OOM kill or automatic restart; Qwen nevertheless reached its 4 GiB cap and recorded memory-max pressure.

| Service | Charged peak bytes | Current bytes | Memory-max events | Automatic restarts | OOM killed |
|---|---|---|---|---|---|
| qwen | 4294967296 | 3532296192 | 11783 | 0 | False |
| stt | 981143552 | 680144896 | 0 | 0 | False |
| tts | 1921519616 | 1272434688 | 0 | 0 | False |
| backend | 112541696 | 94613504 | 0 | 0 | False |
| asterisk | 154800128 | 71507968 | 0 | 0 | False |
| frontend | 25542656 | 20234240 | 0 | 0 | False |

Evidence: artifacts/phase8/cgroup-memory-final.json. CPU cumulative counters and throttle counts are preserved there; per-attempt CPU/memory samples are in each SIP resources.json. Earlier sampled swap and host headroom are not final peak measurements. Increasing Docker allocation or changing Qwen cache settings was not demonstrated safe on this loaded 16 GB host.
