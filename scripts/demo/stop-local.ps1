$ErrorActionPreference = 'Stop'
$voiceRepo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$voiceEnv = Join-Path $voiceRepo 'artifacts/local-demo/compose.env'
$voiceCompose = Join-Path $voiceRepo 'semantic_os/deploy/compose.cpu-voice.yml'
& docker compose -p testmid-cpu-voice --env-file $voiceEnv -f $voiceCompose down --timeout 30
if ($LASTEXITCODE -ne 0) { throw 'Scoped demo shutdown failed' }
Write-Output 'Only testmid-cpu-voice was stopped. Model caches, database and unrelated containers remain.'
