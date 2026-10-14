# Performance baseline and results

Before 2026-10-11T17:39:31.876901+00:00; after 2026-10-11T19:55:31.458537+00:00. Command: `python scripts/benchmark_phase11.py --samples 20 --output artifacts/phase16/api-final.json`. Matched input:1000 synthetic conversations, single concurrency, in-process ASGI/in-memory SQLite, mock providers,20samples. Host load was not controlled; unrelated CPU-busy containers were observed and untouched. No causal optimization or capacity claim.

| Route | Before p50/p95/p99 ms | After p50/p95/p99 ms |
| --- | --- | --- |
| assistants | 16.1217/21.1522/27.9967 | 11.0193/13.572/14.8825 |
| conversation_list | 38.4767/56.1088/95.3839 | 41.7234/61.1572/94.8369 |
| conversation_page | 12.9489/14.9024/15.248 | 16.5308/20.1293/20.7909 |
| operations | 8.1721/10.0989/10.5059 | 7.9971/8.3308/9.6964 |
| booking_three_turns_http | 55.7967/63.4688/68.2849 | 76.5283/135.0516/140.5351 |

Empty-detail fixture is a2-byte response, not a long-conversation benchmark. Existing UI already uses50-row pagination; new team-unread metadata adds payload/query work. Lazy routes are retained. Mobile/slow-network matched before/after metrics are not completed. Inherited Phase15 local samples: desktop LCP1412ms/INP480ms/CLS0; mobile mixed-resize LCP1832/INP992/CLS0; one unthrottled automated session each, not p75 or meeting INP target. No new Qwen/STT/TTS/voice benchmark or peak RAM is invented. Staging CPU/memory snapshot is in `artifacts/phase16/staging-resources.txt`; it is not peak/capacity evidence.


Evidence checkpoint: 11 October 2026, Europe/Sofia. Code is on separate `codex/phase16-saas-operations` branches. No Phase 16 main push/merge or production website deployment. Local feature scope was explicitly approved; the isolated synthetic HTTPS host and Google setup were subsequently authorized. Real Calendar/email actions and real payments remain separately gated.

Executed commands: `.venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests` (328 passed,101.860s; `artifacts/phase16/release-backend.txt`); frontend `npm.cmd test` (31 passed; `verified-frontend.txt`), `npm.cmd run lint -- --fix`, `npm.cmd run typecheck`, `npm.cmd run build`; Docker production-auth frontend build and backend image build with redacted Gitleaks; `python scripts/check_source.py` (236 files,0 failures); network-disabled redacted source scan (434 non-ignored files,2.61MB,no leaks). Logs are ignored under `artifacts/phase16`. These results do not certify legal compliance, live voice, provider billing or physical devices.

Owner/external gates: scoped public staging browser approval is pending after automatic review rejected inspection outside the prior local synthetic scope; actual iOS/Android and screen-reader access are unavailable; English live reschedule/mail receipt, actual reminder delivery, human-heard voice and real billing-provider certification remain unverified. No unexecuted check is PASS.


Latest runtime snapshot: backend57.91MiB, frontend4.734MiB, widget4.07MiB, TLS27.51MiB; VM969MiB total/319MiB available, no swap. Idle single snapshot, not peak.

Actual local320px browser geometry exposed main content at817.4px due to expanded navigation. Mobile menu disclosure was implemented from this evidence; final geometry/keyboard recheck follows local rollout. A real startup clock=None bug was found and fixed using the existing billing/runtime clock, with a regression test. These integration findings were not hidden by the passing injected-clock fixtures.


## Local browser integration checkpoint

Approved local Phase15 Synthetic Workspace, 320px Chromium viewport: Health Center failure exposed a missing default clock; fixed to reuse billing/runtime clock and covered by a new regression. Full backend328 tests pass in101.860s. Health loads in Bulgarian; Usage loads without alerts, switches to English, menu expands/closes and route focus moves to main. Document scrollWidth305 equals clientWidth305. Main content initially started817.4px below the top; measured mobile menu fix places it244.4px below the top, and route navigation focuses it. This is local synthetic geometry/keyboard evidence, not physical-device/screen-reader or final public browser acceptance. Captures: artifacts/phase16/browser/local-health-320.png and local-usage-320.png; earlier health capture is the before image. No real conversation or callback was inspected.
