# Extracted syntax fixture only; use the actual hardware/ runners.
throw 'This file is a syntax-only migration audit fixture.'
$ErrorActionPreference = 'Stop'
$biasDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$biasExecutable = if ($env:CURALINK_LTSPICE_EXE) { $env:CURALINK_LTSPICE_EXE } else { Join-Path $env:LOCALAPPDATA 'Programs/ADI/LTspice/LTspice.exe' }
foreach ($biasCase in @('shared47-op','shared4R7-op','split47-op','shared47-ac','shared4R7-ac','split47-ac')) {
    $biasProcess = Start-Process -FilePath $biasExecutable -ArgumentList '-b','-ascii',($biasCase+'.cir') -WorkingDirectory $biasDirectory -WindowStyle Hidden -Wait -PassThru
    $biasProcess.ExitCode | Set-Content -Path (Join-Path $biasDirectory ($biasCase+'.exitcode.txt'))
    if ($biasProcess.ExitCode -ne 0) { throw "LTspice returned $($biasProcess.ExitCode) for $biasCase" }
    Write-Output ($biasCase + ': exit ' + $biasProcess.ExitCode)
}
