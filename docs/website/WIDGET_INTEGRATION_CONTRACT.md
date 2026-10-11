# Shared widget contract v1 / Phase 13B

Website owns only presentation and two build-time public fields: `VITE_ASSISTANT_WIDGET_ORIGIN` and `VITE_ASSISTANT_PUBLIC_ID`. No tenant identifier, staff bearer, model URL/key, GCS credentials, SIP credential or system prompt is embedded. test_mid resolves the public identifier into an immutable published tenant/version/conversation binding.

The classic async loader is `/widget/assets/v1.js`. Default mode retains the existing floating widget. For a native website wrapper, place the script inside its mount container with `data-mode="embedded"`, `data-assistant-id="wdg_…"` and `data-locale="bg-BG"` or `en-US`. The wrapper loads it only after a user gesture. This is one shared loader/iframe/runtime, not a second chat implementation.

Scope-local events on the script element:

| Event | Meaning |
|---|---|
| testmid-widget-ready | Bound iframe reports successful server session redemption; script load alone is insufficient |
| testmid-widget-error | Bootstrap/iframe error or timeout; no privileged details |
| testmid-widget-expired | Show safe retry while retaining iframe deletion controls |
| testmid-widget-reset | Successful clear: dispose the old mount and return to the entry button |
| testmid-widget-close | Visitor asks native wrapper to close and restore focus |
| testmid-widget-destroy | Wrapper unmount/retry: abort pending fetch, listeners/timer and remove iframe host |

These are presentation signals, not authority or installation certification. The host obtains only a 60-second single-use admission ticket from its exact verified Origin. Parent/iframe messages validate exact source/origin, namespace, public ID, nonce and schema; target origin is explicit. Iframe redemption returns a 10-minute session capability kept only in iframe memory. No capability is sent through DOM events or URLs.

Public widget operations remain admission, redeem, messages, history and confirmed clear. A message includes only content, event_id and optional locale. Retry uses the same unchanged event; changed replay fails. Every business action rechecks session epoch/expiry/version and tenant tool policy. Website code cannot choose tools, tenant or conversation ID.

The safe appearance enum adds `ontelyx-dark` using inspected navy/cyan/system-font tokens. No tenant executable CSS/HTML or arbitrary theme program is supported. Current demo uses approved public FAQ configuration in `semantic_os/config/ontelyx_public_demo.json`, seven-day chat-text retention and synthetic calendars. Contact links use the existing website contact page; no automatic contact send occurs.

Browser voice capability remains false and microphone is denied by iframe and review-site policy. Existing `WebSocketAudioTransport`/`/voice/media` is a browser-compatible JSON media transport component with scoped one-use tickets, asynchronous STT/tool workers and cleanup. It is currently private voice infrastructure, not a verified public widget microphone bridge. Public visitor voice start/stop/capture/playback remains unavailable pending separate acoustic consent, BG/EN speech and browser acceptance. Do not put staff or SIP credentials into website code to bypass this gate.

Read `docs/phase12/EMBED_SECURITY.md`: Origin can be forged outside browsers, quotas are not a network DDoS defense, and text clear retains separate business/audit records. Cloud/edge abuse controls and full browser security review remain open gates.
