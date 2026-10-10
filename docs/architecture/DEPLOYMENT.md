# Deployment and approval gates

Supported topology: a single Uvicorn process with local SQLite/WAL and the existing bounded worker. Do not place its live database on a shared network filesystem or deploy horizontal replicas as a capacity claim. Backend/frontend images are non-root; dependency constraints and lockfiles are used. Production artifacts require reviewed image digests, managed identity/keyring/TLS and operator ownership.

## Local/testing

Follow README for the development app. `scripts/preview_assistant.py` is an explicit ephemeral loopback fixture, not a production entrypoint. Backend tests use synthetic providers; frontend tests include translation-key coverage and exact integer currency formatting. CI performs dependency audits, syntax/import boundaries, tests, frontend typecheck/lint/build, migration validation and offline demonstration artifacts. Gitleaks scans source. A failing critical check prevents proceeding to release; the workflow does not automatically deploy production.

## Isolated staging rehearsal

```powershell
python scripts/prepare_staging.py
docker build -f semantic_os/Dockerfile -t test-mid-assistant:phase5-check semantic_os
docker build -f semantic_os/frontend/Dockerfile -t test-mid-frontend:phase5-staging --build-arg VITE_API_URL=/backend --build-arg VITE_AUTH0_DOMAIN=identity.staging.example.invalid --build-arg VITE_AUTH0_CLIENT_ID=synthetic-staging-client --build-arg VITE_AUTH0_AUDIENCE=staging-api semantic_os
docker compose --env-file artifacts/staging/staging.env -f semantic_os/deploy/compose.staging.yml up -d --wait
python scripts/check_staging.py
docker compose --env-file artifacts/staging/staging.env -f semantic_os/deploy/compose.staging.yml down
```

This project binds only 127.0.0.1:8443 and uses self-signed local TLS, an explicitly enabled synthetic RS256/JWKS issuer, mock billing/channels and dedicated volumes. No actual identity/provider account is represented. `staging_fixture.py` refuses production or live delivery flags. Generated private material is confined to ignored artifacts; no secrets are printed or included in frontend artifacts. Keep the encryption key stable if retaining this fixture volume. Volumes are retained on shutdown; do not use `down -v` against data that you intend to keep.

HTTPS certificate validation, signed identity, tenant denial, bilingual shared conversations, billing metadata, worker/backups and fresh-target restore are tested. The browser separately exercises HTTPS billing in Bulgarian. See STAGING_VERIFICATION.json. Gateway runtime/temp paths are explicitly writable by the unprivileged nginx user.

## Production recipe

`semantic_os/deploy/compose.production.yml` supplies read-only filesystems, writable data/backup volumes, TLS edge, no public backend port, one process, shutdown grace and managed configuration. Its live flags and mock payment enablement remain false. Supply real image digests and certificate permissions readable by the edge user; never substitute staging keys/accounts. Build the frontend with `/backend` and the actual approved custom identity domain, generating an origin-specific CSP.

Readiness checks database access, identity/keyring/catalog configuration and enabled worker/backup prerequisites. Production Swagger is disabled. Configure a platform subject and enabled plan catalog through an authenticated platform operator before admitting tenants. New organizations must prove administrator email through configured verified identity claims. Payment, provider onboarding, public DNS/TLS/certificate renewal, offsite backups, logs/alerts, privacy/tax and real capacity gates remain outstanding; the repository does not activate real collection.

## Release/rollback workflow

Run checks and the staging/recovery rehearsal; retain reports and reviewed image digests; have the deployment owner review identity/provider/TLS/backup/retention and subscription settings; then explicitly approve the actual target deployment. No production target, SSH credentials or public deployment was provided or launched in this task. Hosted GitHub Actions execution is not claimed; its checks were reproduced locally.

Before deployment, capture a verified encrypted snapshot and drain work. Migrations only move forward. Roll back to a compatible application image without deleting columns/tables; if schema compatibility cannot be guaranteed, stop traffic and restore to a new database path, validate and explicitly switch it. Preserve app/backup keys and reconcile external sending/uncertain jobs before re-enabling workers. Never reverse applied migrations or overwrite a live database automatically.

Current remaining scale limits: one writer lock, unpaginated history, local memory aggregates/rate limiter, bounded voice executor, and unverified real provider latency/quotas. See PERFORMANCE_RESULTS.json; no concurrent production-call count is promised.
