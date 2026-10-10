# Read-only demo health command

Run from test_mid:

```powershell
powershell.exe -NoProfile -File scripts/demo/readiness.ps1
```

Python equivalent: `.venv/Scripts/python.exe scripts/demo_readiness.py`. Report: artifacts/phase9/readiness.json. Python/PowerShell wrapper return 2 when blocked; a parent shell may represent a failing native command differently. Read the explicit JSON decision, not just a shell success icon.

RUNNING means an owned process exists. HEALTHY means an actual health/HTTP/configuration probe passed. VERIFIED is limited to the stated database/tenant/configuration/fixed-slot check. BLOCKED means missing/failed evidence with a remaining action. None alone proves caller-heard speech or visible dashboard bookings.

Checks: six project-owned containers/image IDs; Asterisk PJSIP endpoint 1001; Qwen model health; existing STT/TTS health; ARI gateway; backend API; read-only SQLite integrity/foreign keys/migration 5; marked SmileCare tenant/two dentists; both agents/booking tools; voice/Web Chat and one concurrent session; HTTP dashboard; fixed future slots through the existing mock calendar and authoritative appointment reads. It reads Phase 8B receipts and fails closed on missing human/UI/acoustic evidence or duplicate booking IDs.

No call, reservation, reset, model download, inference-worker duplication or external send occurs. It never serializes environment variables/secret values. Qwen/STT/TTS process health does not replace actual inference/pronunciation tests. SIP endpoint presence establishes configuration capability, not new registration or PSTN access. HTTP 200 is not visual UI verification.

The blocked audit is intentional. See PHASE9_READINESS.md and DEMO_TROUBLESHOOTING.md. Do not change a result field to remove a blocker; obtain and retain new real evidence after correcting the underlying problem.
