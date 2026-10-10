param([switch]$Confirm)
$ErrorActionPreference = 'Stop'
if (-not $Confirm) { throw 'Explicit -Confirm is required to archive only the marked fictional demo; no reset was performed' }
$voiceRepo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$voiceEnv = Join-Path $voiceRepo 'artifacts/local-demo/compose.env'
$voiceCompose = Join-Path $voiceRepo 'semantic_os/deploy/compose.cpu-voice.yml'
$voiceRunning = & docker compose -p testmid-cpu-voice --env-file $voiceEnv -f $voiceCompose ps -q --status running
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify the demo is stopped; reset refused before database access. Restore Docker diagnostics first.' }
if ($voiceRunning) { throw 'Stop only the local demo before archiving its data' }
Set-Location -LiteralPath $voiceRepo
& "$voiceRepo/.venv/Scripts/python.exe" scripts/smilecare_demo.py reset --confirm --database .assistant-data/cpu-voice-demo/assistant.sqlite3
if ($LASTEXITCODE -ne 0) { throw 'Tenant-scoped reset rejected or failed' }
