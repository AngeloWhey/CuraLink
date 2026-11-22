# Extracted syntax fixture only; use the actual hardware/ runners.
throw 'This file is a syntax-only migration audit fixture.'
$ErrorActionPreference = 'Stop'
$siDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$siExecutable = if ($env:CURALINK_LTSPICE_EXE) { $env:CURALINK_LTSPICE_EXE } else { Join-Path $env:LOCALAPPDATA 'Programs/ADI/LTspice/LTspice.exe' }
foreach ($siCase in @('valid-operating-point','ch1-only','input-input','output-input')) {
    $siProcess = Start-Process -FilePath $siExecutable -ArgumentList '-b','-ascii',($siCase+'.cir') -WorkingDirectory $siDirectory -WindowStyle Hidden -Wait -PassThru
    $siProcess.ExitCode | Set-Content -Path (Join-Path $siDirectory ($siCase+'.exitcode.txt'))
    if ($siProcess.ExitCode -ne 0) { throw "LTspice returned $($siProcess.ExitCode) for $siCase" }
    Write-Output ($siCase + ': exit ' + $siProcess.ExitCode)
}
