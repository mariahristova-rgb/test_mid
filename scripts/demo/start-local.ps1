param([switch]$Build, [switch]$Provision, [switch]$NeuralVoice)
$ErrorActionPreference = 'Stop'
$voiceRepo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location -LiteralPath $voiceRepo
if ($Provision) {
  & "$voiceRepo/.venv/Scripts/python.exe" scripts/provision_speech.py --cache .assistant-model-cache/speech
  if ($LASTEXITCODE -ne 0) { throw 'Speech provisioning failed' }
}
$voicePrepareArgs = @('scripts/prepare_cpu_demo.py')
if ($NeuralVoice) { $voicePrepareArgs += '--neural' }
& "$voiceRepo/.venv/Scripts/python.exe" @voicePrepareArgs
if ($LASTEXITCODE -ne 0) { throw 'Private demo preparation failed' }
$voiceEnv = Join-Path $voiceRepo 'artifacts/local-demo/compose.env'
$voiceCompose = Join-Path $voiceRepo 'semantic_os/deploy/compose.cpu-voice.yml'
$voiceArgs = @('compose','-p','testmid-cpu-voice','--env-file',$voiceEnv,'-f',$voiceCompose)
if ($NeuralVoice) { $voiceArgs += @('-f',(Join-Path $voiceRepo 'semantic_os/deploy/compose.cpu-neural.yml')) }
& docker @voiceArgs config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Invalid local compose configuration' }
$voiceModel = Join-Path $voiceRepo '.assistant-model-cache/converted/Qwen3-4B/hf-1cfa9a7208912126459214e8b04321603b3df60c/conversion.json'
if (-not (Test-Path -LiteralPath $voiceModel)) { throw 'Verified Q4_K_M conversion is required before starting; see LOCAL_MODEL_SETUP.md' }
& "$voiceRepo/.venv/Scripts/python.exe" scripts/verify_cpu_cache.py
if ($LASTEXITCODE -ne 0) { throw 'Model integrity check failed' }
if ($Build) {
  & docker @voiceArgs build
  if ($LASTEXITCODE -ne 0) { throw 'Local image build failed' }
}
& "$voiceRepo/.venv/Scripts/python.exe" scripts/stage_qwen_volume.py
if ($LASTEXITCODE -ne 0) { throw 'Project-owned Linux model volume verification failed' }
& docker @voiceArgs up -d --wait --wait-timeout 300
if ($LASTEXITCODE -ne 0) { throw 'Services are not healthy; inspect check-local.ps1 and scoped logs' }
Write-Output 'Local services started. This is not proof of a successful SIP booking.'
