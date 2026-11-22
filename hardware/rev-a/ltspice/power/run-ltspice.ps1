param([string[]]$Files = @())
$ErrorActionPreference = 'Stop'
$taskDirectory = $PSScriptRoot
$ltExecutable = if ($env:CURALINK_LTSPICE_EXE) { $env:CURALINK_LTSPICE_EXE } else { Join-Path $env:LOCALAPPDATA 'Programs/ADI/LTspice/LTspice.exe' }
if ($Files.Count -eq 0) {
    $Files = @(Get-ChildItem -LiteralPath $taskDirectory -Filter '*.cir' -File | Select-Object -ExpandProperty Name)
}
foreach ($file in $Files) {
    $inputPath = Join-Path $taskDirectory $file
    $runProcess = Start-Process -FilePath $ltExecutable -ArgumentList @('-b','-ascii',('"' + $inputPath + '"')) -WorkingDirectory $taskDirectory -WindowStyle Hidden -Wait -PassThru
    Write-Output ($file + ' exit=' + $runProcess.ExitCode)
    $logPath = [System.IO.Path]::ChangeExtension($inputPath, '.log')
    if (Test-Path -LiteralPath $logPath) {
        Get-Content -LiteralPath $logPath | Select-Object -Last 22
    }
}
