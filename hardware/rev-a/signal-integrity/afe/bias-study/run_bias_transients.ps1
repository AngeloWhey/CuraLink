$ErrorActionPreference = 'Stop'
$biasDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$biasExecutable = if ($env:CURALINK_LTSPICE_EXE) { $env:CURALINK_LTSPICE_EXE } else { Join-Path $env:LOCALAPPDATA 'Programs/ADI/LTspice/LTspice.exe' }
foreach ($biasCase in @('split4R7-op','split4R7-ac','shared4R7-startup','shared4R7-offset-recovery','shared4R7-load-step','split4R7-startup','split4R7-offset-recovery','split4R7-load-step')) {
    $biasProcess = Start-Process -FilePath $biasExecutable -ArgumentList '-b','-ascii',($biasCase+'.cir') -WorkingDirectory $biasDirectory -WindowStyle Hidden -Wait -PassThru
    $biasProcess.ExitCode | Set-Content -Path (Join-Path $biasDirectory ($biasCase+'.exitcode.txt'))
    if ($biasProcess.ExitCode -ne 0) { throw "LTspice returned $($biasProcess.ExitCode) for $biasCase" }
    Write-Output ($biasCase + ': exit ' + $biasProcess.ExitCode)
}
