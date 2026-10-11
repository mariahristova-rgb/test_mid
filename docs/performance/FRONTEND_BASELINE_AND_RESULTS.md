# Frontend baseline and results

10 October 2026; same local host and Vite 8.3.4 production build workflow. Baseline is source 213e0ce. No browser Web Vitals or render profiling could be captured because local browser inspection is blocked.

| Static build measure | Before | After |
|---|---|---|
| Entry JavaScript | 208.83 kB / 67.25 kB gzip | 186.68 kB / 65.12 kB gzip |
| Total emitted JavaScript | 208.83 kB | 269.54 kB |
| CSS | 11.88 kB / 3.63 kB gzip | 13.91 kB / 4.21 kB gzip |
| Routes | Eager Workspace + SaaS | Lazy Workspace, SaaS and Setup |
| Workspace assistant page API plan | Ten reads | Bootstrap + assistants (two reads) |
| Workspace dashboard polling | Calls + appointments + bootstrap | Bootstrap only |

Entry reduction is 22.15 kB (10.61% raw), not an overall responsiveness claim. A first dashboard visit also loads Workspace (53.10 kB) and shared EmptyState (0.90 kB): raw JavaScript can exceed the old single bundle. Total JS grows with new functionality. A lazy Auth0 experiment generated an extra 216.30 kB SDK chunk and was removed; the existing Auth0 loading behavior is retained.

Commands: npm run lint; npm run typecheck; npm test; npm run build from semantic_os/frontend. Final build output: artifacts/phase11-frontend-build.txt. Route plans are covered by workspace.test.mjs; superseded initial reads are aborted and stale route results discarded. Inbox pages are bounded at 50 rather than loading all conversations. No unmeasured virtualization/memoization or new chart dependency was introduced.

LCP, INP, CLS, p75 field data, route timing, long tasks, browser memory growth, rendered-component counts and visual comparison are UNMEASURED. Aspirational targets remain LCP≤2.5s, INP≤200ms, CLS≤0.1 at p75. Do not infer these from build time or bundle size. Remaining work: authorized browser instrumentation and before/after workloads on the same device; production Auth0 bundle/runtime validation.
