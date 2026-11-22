param(
    [string[]]$Cases = @(
        'import-tlv9002-op', 'import-tlv9052-op', 'afe-full-op',
        'afe-dc-differential-offset', 'afe-dc-common-offset',
        'afe-ac-differential', 'afe-ac-common',
        'afe-dc-capacitor-leakage-qualified', 'afe-offset-recovery-long', 'afe-startup'
    )
)

$ErrorActionPreference = 'Stop'
$ltspiceExecutable = if ($env:CURALINK_LTSPICE_EXE) { $env:CURALINK_LTSPICE_EXE } else { Join-Path $env:LOCALAPPDATA 'Programs/ADI/LTspice/LTspice.exe' }
if (-not (Test-Path -LiteralPath $ltspiceExecutable)) {
    throw "Installed LTspice executable not found: $ltspiceExecutable"
}
foreach ($case in $Cases) {
    if ($case -notmatch '^[a-z0-9-]+$') { throw "Invalid analysis name: $case" }
    $deckPath = Join-Path $PSScriptRoot ($case + '.cir')
    if (-not (Test-Path -LiteralPath $deckPath)) { throw "Deck missing: $deckPath" }
    Write-Output "Running $case in actual LTspice (hidden batch)."
    $ltTaskProcess = Start-Process -FilePath $ltspiceExecutable `
        -ArgumentList '-b', '-ascii', ($case + '.cir') `
        -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -Wait -PassThru
    $ltTaskProcess.ExitCode | Set-Content -LiteralPath (Join-Path $PSScriptRoot ($case + '.exitcode.txt'))
    if ($ltTaskProcess.ExitCode -ne 0) {
        throw "LTspice returned $($ltTaskProcess.ExitCode) for $case; inspect its log and raw data."
    }
}
Write-Output 'Batch runs completed. Run analyze_afe_ltspice.py to inspect operating points and criteria; exit code alone is not validation.'
