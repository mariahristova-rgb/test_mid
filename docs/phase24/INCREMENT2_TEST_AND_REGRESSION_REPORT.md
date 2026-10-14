# Increment 2 test and regression report

14 October 2026. All commands use existing approved offline infrastructure. Exactcommands fromtest_mid:

- `.venv/Scripts/python.exe -m unittest semantic_os.backend.tests.test_ux` (redirecttoartifacts/phase24/increment2-targeted.txt):28PASS6.464s.
- `.venv/Scripts/python.exe -m unittest discover -s semantic_os/backend/tests` (increment2-backend.txt):356PASS60.756s.
- `.venv/Scripts/python.exe scripts/evaluate_phase17.py --output artifacts/phase24/increment2-evaluations.json`:version1.4.1,46/46PASS,pilot_readyfalse,mocktokenusageunmeasured.
- `.venv/Scripts/python.exe scripts/check_migrations.py --output artifacts/phase24/increment2-migrations.json`:schema1–5,integrity/FKs/datapreservationPASS.
- `.venv/Scripts/python.exe scripts/check_source.py`:244files/0failures.
- `node semantic_os/security/scan-secrets.mjs semantic_os/backend semantic_os/frontend/src semantic_os/config scripts docs/phase24`:342 files PASS;notfreshGitleaks/hostedCIproof.
- semantic_os/frontend:`npm run test`39PASS;`npm run typecheck`,`npm run lint`,`npm run build`PASS. Artifactsincrement2-frontend.txt/increment2-build.txt. ESLintlocalSetupViewformatfixused;noframework/dependencychange.
- artifacts/phase13b/ontelyx:`npm run test`72Vitest+6NodePASS;`npm run test:config`,`npm run build`,`npm run format:check`PASS. increment2-website.txt/increment2-website-build.txt;websiteworkingtreeunchanged.
- `git -c core.whitespace=cr-at-eol diff --check`:PASS;localeCRLFpreserved.

CUAread-onlyDOM/focusandnormalformactions used onlyfreshsyntheticloopbackfixture. BrowserFAQ8casePASS,dirty-readinessstale,two-editorconflict/discardreloadPASS;boundaries andfailedviewportattempt recorded inSETUP_ACCESSIBILITY_REPORT.md. Screenshotsdisplayed butnotclaimedasfileartifacts.

Remainingwarning:Starlette/httpxdeprecationexisting. No finalautomatedtestfailure. Browser390viewportdidnottakeeffect;fullAT/mobile/keyboardmanualacceptance remainsNOTTESTED. Sessionendedbetweenuserturns,serverrestartedwithnewin-memorydatabase;onefailedoldtabdata-errorURLbindingwasnotbypassed. LocatorerrorsresolvedwithfreshDOM. No newexecutionissue was hiddenasPASS.
