# Fresh merged-tree regression evidence
Executed 2026-10-14. Local synthetic/offline scope only.

| Exact command | Actual outcome |
| --- | --- |
| .venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests | 382 passed, 58.236 seconds |
| npm test (semantic_os/frontend) | 45 passed |
| npm run typecheck (semantic_os/frontend) | PASS |
| npm run lint (semantic_os/frontend) | PASS, zero warnings |
| npm run build (semantic_os/frontend) | PASS, source and output environment-secret scans passed |
| .venv/Scripts/python.exe scripts/evaluate_phase17.py --output artifacts/phase26a-evaluations.json | 64/64 OFFLINE_CONTRACT_ONLY; pilot_ready=false |
| .venv/Scripts/python.exe scripts/check_source.py | 262 files, zero failures |
| .venv/Scripts/python.exe scripts/check_migrations.py --output artifacts/phase26a-migrations.json | schema versions 1–5; integrity, foreign keys and data preservation PASS |
| node semantic_os/security/scan-secrets.mjs semantic_os/backend/assistant semantic_os/backend/tests semantic_os/frontend/src docs/phase26 | 228 files PASS (environment-secret check; not equivalent to Gitleaks) |
| npm test (artifacts/phase13b/ontelyx) | 72 Vitest + 6 Node tests PASS |
| git -c core.whitespace=cr-at-eol diff --check | PASS |

Initial command errors: npm typecheck was initially called from repository root without package.json; corrected working directory passed. Migration initially failed opening sandbox temporary DB; authorized offline retry passed. Backend emits a Starlette/httpx deprecation warning, not a failure. Website tests required authorized process spawning.

Ignored artifacts retain backend log and machine-readable migration/evaluation outputs. Remote CI, dependency advisory checks and Gitleaks receipt remain pending. Browser acceptance is recorded separately and must not be inferred from unit tests.

