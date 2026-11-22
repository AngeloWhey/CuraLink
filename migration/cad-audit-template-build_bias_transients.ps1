# Extracted syntax fixture only; use the actual hardware/ runners.
throw 'This file is a syntax-only migration audit fixture.'
$ErrorActionPreference = 'Stop'
$biasDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$biasExecutable = if ($env:CURALINK_LTSPICE_EXE) { $env:CURALINK_LTSPICE_EXE } else { Join-Path $env:LOCALAPPDATA 'Programs/ADI/LTspice/LTspice.exe' }
foreach ($biasCase in @('SYNTAX_ONLY_PLACEHOLDER')) {
    $biasProcess = Start-Process -FilePath $biasExecutable -ArgumentList '-b','-ascii',($biasCase+'.cir') -WorkingDirectory $biasDirectory -WindowStyle Hidden -Wait -PassThru
    $biasProcess.ExitCode | Set-Content -Path (Join-Path $biasDirectory ($biasCase+'.exitcode.txt'))
    if ($biasProcess.ExitCode -ne 0) { throw "LTspice returned $($biasProcess.ExitCode) for $biasCase" }
    Write-Output ($biasCase + ': exit ' + $biasProcess.ExitCode)
}
