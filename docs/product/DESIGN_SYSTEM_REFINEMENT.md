# Design system refinement

11 October 2026. Local feature branch `codex/phase15-product-experience`; no Phase 15 push/merge/public deployment. Existing URLs and the two-agent runtime are retained.


Assistant tokens are in frontend/src/assets/main.css: 4/8/12/16/24 spacing, radius12, focus outline and 44px controls. Website tokens in ontelyx/src/styles.css and iframe styles in semantic_os/widget/frame.css are retained. No brand artwork, private semantic source or new icon/chart dependency is copied.

Phase15 changes reuse native buttons, details, form labels, role=alert/status, existing controls/cards and spacing tokens. Queue notes use Vue text interpolation (no HTML rendering). New group heading density uses existing spacing; mobile nav wraps. The existing debugger is already three-column with stacked/mobile panels; raw transcript arguments remain outside metadata diagnostics.

Status policy: NOT_CONFIGURED means no integration; MOCK means synthetic provider; CONFIGURED means settings/process metadata, TESTED means scoped simulation receipt, LIVE_VERIFIED requires named external receipt, BLOCKED requires a specific unmet gate. A connected Google account or healthy model process is not globally Ready. No new health center is implemented yet.

Open acceptance: 320/360/375/390/430/768/1024/1440, landscape, 200% zoom, keyboard and screen reader for changed assistant screens. Prior Watch Demo screenshots cover only that modal and cannot certify the new Inbox. Browser auto-review rejected Phase15 inspection. No WCAG2.2 AA or representative-device claim.


Approved synthetic browser follow-up verified no horizontal document overflow at320/360/375/390/430/768/1024/1440. Source now collapses five Inbox filters by default, uses the actual organization name, separates Bulgarian open-status from open-action wording, and distinguishes outbound human provenance. Representative screenshot evidence is under artifacts/phase15/browser. Rapid viewport capture initially produced stale painted frames; separate fresh captures were used. Physical iOS/Android, screen-reader and native200%zoom acceptance are not claimed.
