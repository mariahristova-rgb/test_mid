$ErrorActionPreference = 'Stop'
$voiceRepo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$voiceEnv = Join-Path $voiceRepo 'artifacts/local-demo/compose.env'
$voiceCompose = Join-Path $voiceRepo 'semantic_os/deploy/compose.cpu-voice.yml'
$voiceArgs = @('compose','-p','testmid-cpu-voice','--env-file',$voiceEnv,'-f',$voiceCompose)
& docker @voiceArgs ps
$voiceIds = & docker @voiceArgs ps -q
if ($voiceIds) { & docker stats --no-stream $voiceIds }
& docker @voiceArgs exec -T asterisk asterisk -rx 'pjsip show contacts'
& docker @voiceArgs exec -T asterisk asterisk -rx 'ari show apps'
Write-Output 'Health/registration diagnostics do not establish speech, booking or three-call readiness.'
