# Staging deployment contract

Existing deployment files: `semantic_os/deploy/phase15-staging/{compose.yml,bootstrap.py,Caddyfile,nginx.conf,startup.sh,install-package.sh}`. Package script: `scripts/package_phase16_staging.py`. No Phase 17 deployment executed.

Assistant base d6da61f and website base 1d40ddd use the existing loader/iframe/API and assistant revision snapshots. Phase 17 privacy change preserves wire schemas; evaluation corpus version 1.0.0 is an offline contract artifact, not a widget protocol version. Deployments currently use reviewed image tags and package hash receipts, not a complete enforced protocol-version negotiation matrix. That matrix and canary version rejection are still required before independent component rollouts.

Website production configuration is unchanged. Do not point it at the synthetic FAQ-only tenant as a real booking service. Localhost demo origins are restricted to local development; public origins are the three explicitly named HTTPS hosts. Staff API is excluded from public proxy. Secret references remain server-side.

Preserve the existing persistent disk and encryption key, owner-only identity, 1GB public response quota and fixed Oct14 stop. Rollback requires compatible image/config receipts and data integrity checks; do not restore over a live database or replay uncertain jobs. Fresh remote inventory and deployed restore rehearsal remain pending authorization and evidence.
