$ErrorActionPreference = 'Stop'
$taskDirectory = $PSScriptRoot
$ltExecutable = if ($env:CURALINK_LTSPICE_EXE) { $env:CURALINK_LTSPICE_EXE } else { Join-Path $env:LOCALAPPDATA 'Programs/ADI/LTspice/LTspice.exe' }
foreach ($file in @('afe-avdd-ripple.cir', 'afe-vmid-current.cir')) {
    $inputPath = Join-Path $taskDirectory $file
    $runProcess = Start-Process -FilePath $ltExecutable -ArgumentList @('-b','-ascii',('"' + $inputPath + '"')) -WorkingDirectory $taskDirectory -WindowStyle Hidden -Wait -PassThru
    Write-Output ($file + ' exit=' + $runProcess.ExitCode)
    Get-Content -LiteralPath ([System.IO.Path]::ChangeExtension($inputPath, '.log')) | Select-Object -Last 18
}
