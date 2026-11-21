
# Part 1A - Independent Deterministic Harness
# Run from the Part-1A project root.

$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EvidenceDir = Join-Path $ProjectRoot "evidence\harness-results"

New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LogFile = Join-Path $EvidenceDir "harness-$Timestamp.log"

Set-Location $ProjectRoot

$Results = @()

function Run-Gate {
    param(
        [string]$Name,
        [string]$Module,
        [string[]]$Arguments
    )

    Write-Host "`n========== $Name ==========" -ForegroundColor Cyan

    $Output = & python -m $Module @Arguments 2>&1
    $ExitCode = $LASTEXITCODE

    $Output | ForEach-Object { Write-Host $_ }

    $Output | Out-File -FilePath $LogFile -Append

    if ($ExitCode -eq 0) {
        Write-Host "$Name : PASS" -ForegroundColor Green
        $script:Results += "$Name : PASS"
    }
    else {
        Write-Host "$Name : FAIL (Exit code: $ExitCode)" -ForegroundColor Red
        $script:Results += "$Name : FAIL (Exit code: $ExitCode)"
    }
}

"PART 1A HARNESS EXECUTION - $Timestamp" |
    Out-File -FilePath $LogFile

Run-Gate -Name "RUFF LINT" `
    -Module "ruff" `
    -Arguments @("check", "src", "tests")

Run-Gate -Name "BANDIT SECURITY" `
    -Module "bandit" `
    -Arguments @("-r", "src/inventory_api")

Run-Gate -Name "PYTEST UNIT AND CONTRACT TESTS" `
    -Module "pytest" `
    -Arguments @("tests/", "-v")

$Failed = @($Results | Where-Object { $_ -like "*FAIL*" }).Count

"`n========== FINAL HARNESS SUMMARY ==========" |
    Tee-Object -FilePath $LogFile -Append

$Results | ForEach-Object {
    Write-Host $_
    $_ | Out-File -FilePath $LogFile -Append
}

if ($Failed -eq 0) {
    Write-Host "`nOVERALL RESULT: PASS" -ForegroundColor Green
    "OVERALL RESULT: PASS" | Out-File -FilePath $LogFile -Append
    exit 0
}
else {
    Write-Host "`nOVERALL RESULT: FAIL" -ForegroundColor Red
    "OVERALL RESULT: FAIL" | Out-File -FilePath $LogFile -Append
    exit 1
}
