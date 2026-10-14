# Security and release integrity

Fresh checks13October2026:

| Check | Result | Evidence |
|---|---|---|
| Python lockfile advisory audit | PASS | pip-audit2.10.1,40dependencies/0known findings; artifacts/phase20/python-audit.json |
| Assistant frontend advisory audit | PASS | npm lock-only audit,0findings; frontend-audit.json |
| Website advisory audit | FAIL initially; PASS after approved fix |1high GHSA-68fv-2mgg-jv7q in1.2.1; website-audit.json→website-audit-after.json0findings |
| Authentication/tenant/consent/ownership/redaction regressions | PASS synthetic |67tests/8.461s; security-regressions.txt |
| Source boundaries/syntax/pattern checks | PASS within checker scope |240files/0failures |
| Environment-secret comparison scan | PASS within scanner scope |324files; no matched values exposed |
| Local staging-config archive integrity | PASS | Exact five members/hash matches; release-integrity.json |
| Fresh hosted CI/Gitleaks/deployed image attestation | NOT TESTED | No hosted result or trusted installed scanner/image attestation retrieved |

Commands: `python -m pip_audit -r semantic_os/backend/requirements.lock --no-deps --disable-pip --format json --output artifacts/phase20/python-audit.json`; both repos `npm audit --package-lock-only --ignore-scripts --json`; website `npm update source-map-js --package-lock-only --ignore-scripts`, `npm ci --ignore-scripts`, `npm ls source-map-js --all`, `npm test`, `npm run test:config`, `npm run build`; targeted unittest modules google_owner_login/customer_workspace/google_concierge/widget; `scripts/check_source.py`; `node semantic_os/security/scan-secrets.mjs` on reviewed source directories.

The website lock update changes only version/resolved URL/integrity for source-map-js. No package.json override/new dependency needed. Installed tree confirms1.2.2 through Vue/Vite/test dependencies. Advisory: [GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q), affected>=1.0.0,<1.2.2; indexed source-map offsets can block the event loop. This dependency finding is not evidence of exploitation or a demonstrated attack path against the public static website.

Initial npm audit redirections raced creation of the evidence directory and did not run; repeated after the directory existed. Only actual repeat results above count. pip-audit warned the pinned constraints lack full hashes; zero known advisory findings is not a complete supply-chain/security certificate.

CI source includes offline tests/audits/migration/Gitleaks, but no fresh hostedCI proof. Reviewed application images still use mutable `:reviewed` tags; archive hashes do not attest deployed runtime source or all OCI layers. Lockfile integrity/SHA256 receipts are scoped local evidence. No credentials/logging policy weakened.
