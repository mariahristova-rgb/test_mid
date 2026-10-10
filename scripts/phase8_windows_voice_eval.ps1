param([string]$Locale='bg-BG', [string]$CasesFile='artifacts/phase8/windows-voice-cases.json', [string]$OutputDirectory='artifacts/phase8/windows-voice')
$ErrorActionPreference='Stop'
$voiceRepo=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null=[Windows.Media.SpeechSynthesis.SpeechSynthesizer,Windows.Media.SpeechSynthesis,ContentType=WindowsRuntime]
$null=[Windows.Media.SpeechSynthesis.SpeechSynthesisStream,Windows.Media.SpeechSynthesis,ContentType=WindowsRuntime]
$null=[Windows.Storage.Streams.DataReader,Windows.Storage.Streams,ContentType=WindowsRuntime]
function Await-VoiceResult($Operation,[Type]$ResultType) {
  $voiceMethod=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
  } | Select-Object -First 1
  $voiceTask=$voiceMethod.MakeGenericMethod($ResultType).Invoke($null,@($Operation))
  if (-not $voiceTask.Wait(30000)) { throw 'Local Windows synthesis timed out' }
  return $voiceTask.Result
}
$voiceEngine=New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
$voiceChoice=[Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | Where-Object Language -EQ $Locale | Select-Object -First 1
if (-not $voiceChoice) { throw 'Requested installed local voice is unavailable' }
$voiceEngine.Voice=$voiceChoice
$voiceOutput=[IO.Path]::GetFullPath((Join-Path $voiceRepo $OutputDirectory))
if (-not $voiceOutput.StartsWith(($voiceRepo+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase)) { throw 'Evaluation output must remain in test_mid' }
New-Item -ItemType Directory -Force -Path $voiceOutput | Out-Null
$voiceCases=Get-Content -LiteralPath (Join-Path $voiceRepo $CasesFile) -Encoding UTF8 | ConvertFrom-Json
$voiceResults=@()
foreach ($voiceCase in $voiceCases) {
  if ($voiceCase.locale -ne $Locale) { continue }
  $voiceCpuBefore=(Get-Process -Id $PID).CPU
  $voiceTimer=[Diagnostics.Stopwatch]::StartNew()
  $voiceStream=Await-VoiceResult ($voiceEngine.SynthesizeTextToStreamAsync($voiceCase.text)) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
  $voiceFirstStreamMs=$voiceTimer.Elapsed.TotalMilliseconds
  $voiceReader=New-Object Windows.Storage.Streams.DataReader($voiceStream)
  $null=Await-VoiceResult ($voiceReader.LoadAsync([uint32]$voiceStream.Size)) ([uint32])
  $voiceBytes=New-Object byte[] ([int]$voiceStream.Size)
  $voiceReader.ReadBytes($voiceBytes)
  $voicePath=Join-Path $voiceOutput ($Locale+'-'+$voiceCase.label+'.wav')
  [IO.File]::WriteAllBytes($voicePath,$voiceBytes)
  $voiceTimer.Stop()
  $voiceProcess=Get-Process -Id $PID
  $voiceResults += [pscustomobject]@{locale=$Locale;label=$voiceCase.label;text=$voiceCase.text;voice=$voiceChoice.DisplayName;first_complete_stream_ms=$voiceFirstStreamMs;wall_ms=$voiceTimer.Elapsed.TotalMilliseconds;cpu_ms=1000*($voiceProcess.CPU-$voiceCpuBefore);audio_bytes=$voiceBytes.Length;working_set_bytes=$voiceProcess.WorkingSet64;peak_working_set_bytes=$voiceProcess.PeakWorkingSet64;audio_file=$voicePath;live_replacement=$false}
  $voiceReader.Dispose(); $voiceStream.Dispose()
}
$voiceEngine.Dispose()
$voiceResults | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $voiceOutput ($Locale+'-results.json')) -Encoding UTF8
$voiceResults | Select-Object locale,label,voice,first_complete_stream_ms,wall_ms,audio_bytes,working_set_bytes | ConvertTo-Json -Depth 4
