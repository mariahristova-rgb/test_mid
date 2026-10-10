# Demo performance evidence

DEMO_BLOCKED. No new Phase 9 live voice or Qwen benchmark was run. The table below is explicitly historical Phase 8B data from 9 October 2026, not a newly accepted rehearsal. Subsequent Phase 9 synthetic fixed-date TTS/STT probes are recorded separately; they do not establish live or human acceptance.

| Historical call | Locale | Confirmation STT ms | Consent decision ms | Confirmation TTS ms | Finalized speech → first confirmation packet ms |
|---|---|---|---|---|---|
| 20261009T105422Z-29fa08 | bg-BG | 6351.22 | 0.922 | 8019.24 | 19522.42 |
| 20261009T105839Z-e5d106 | en-US | 6600.60 | 0.301 | 6962.83 | 23881.86 |
| 20261009T110159Z-7f0d1a | bg-BG | 9566.94 | 0.712 | 8778.14 | 26652.29 |

First synchronized human-audible latency and SIP connection duration were not separately measured; no number is invented. Registration/CONFIRMED evidence is retained in the redacted client logs. Model intent/native-tool proposal and existing agent/tool aggregate timings remain in each actual Operations snapshot. Separate compact Qwen probes are historical, not per-call decoder throughput.

Sampled Docker CPU maxima over the three historical calls (100% corresponds to one core-equivalent; sampling can miss peaks):

| Service | Maximum observed CPU % |
|---|---|
| testmid-cpu-voice-asterisk-1 | 12.00 |
| testmid-cpu-voice-backend-1 | 109.44 |
| testmid-cpu-voice-qwen-1 | 460.94 |
| testmid-cpu-voice-stt-1 | 408.78 |
| testmid-cpu-voice-tts-1 | 206.60 |

Historical cgroup charged peaks: Qwen 4,294,967,296 bytes; STT 738,668,544; TTS 1,921,519,616. Peaks cover different service lifetimes/startup/cache/kernel, not simultaneous total RAM. No OOM kill or automatic service restart was observed; Qwen hit its 4 GiB cap. CPU/background workload and development checks varied, so no capacity/SLA guarantee follows. One call and one inference process per service remain.

Use VOICE_LATENCY_RESULTS.md, actual per-call Operations/resources and cgroup-memory-final.json. Development-only Ivan evaluation is much faster in batch, but the active response TTS remains BG38; no production default change is approved. First-audible, fixed-date voice and 8–12-minute presentation timing require a new attended rehearsal after the prerequisite gate passes.
