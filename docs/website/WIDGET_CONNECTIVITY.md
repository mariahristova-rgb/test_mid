# Environment-specific connectivity

Local review: website 127.0.0.1:5173, widget 127.0.0.1:3020, staff app 127.0.0.1:3017. These distinct origins are **development only**, not public deployment URLs. The previously observed refused connection was an nginx redirect to internal 8080; absolute_redirect off preserves the host port.

Website public-config.ts now rejects hosted loopback, literal IP and private/internal service targets; config.ts independently disables a local/private target when the page is hosted publicly, even if a local artifact is accidentally served. Private Docker/inference/SIP/admin endpoints must never become widget origins. .env.staging.example deliberately has blank paired public settings until an approved HTTPS domain/public ID exists. Arbitrary VITE secrets are not exported.

The loader is classic async and gesture-lazy. Exact verified origin admission → one-use ticket → iframe redemption → short-lived scoped session. CORS, frame-ancestors, source/origin/schema/nonce checks and server permissions remain active. Only /widget routes are exposed at the widget proxy. Google configuration/callbacks are on the private staff application proxy; callback access logging is disabled. No Windows tunnel/public exposure is introduced.

Publishing requires real site ownership verification. A GitHub checkout, source build, script HTTP 200 or connected OAuth does not prove browser bootstrap or production readiness. Deployment order: backend/API/static widget first; then website build with approved HTTPS public settings; verify policy and browser network traffic; owner approves public release separately. Asset rollout should account for the existing five-minute cache window.
