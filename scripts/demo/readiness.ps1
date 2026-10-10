$ErrorActionPreference='Stop'
$voiceRepo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
& "$voiceRepo/.venv/Scripts/python.exe" "$voiceRepo/scripts/demo_readiness.py"
if ($LASTEXITCODE -eq 2) { Write-Output 'DEMO_BLOCKED: see artifacts/phase9/readiness.json; healthy services do not waive acceptance'; exit 2 }
if ($LASTEXITCODE -ne 0) { throw 'Read-only readiness audit failed' }
