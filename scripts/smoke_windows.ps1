[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ReaderExe,
    [int]$TimeoutSeconds = 30
)

. (Join-Path $PSScriptRoot "smoke_helpers.ps1")

$ErrorActionPreference = "Stop"
$resolvedExe = (Resolve-Path $ReaderExe).Path
$runId = [Guid]::NewGuid().ToString("N")
$testRoot = Join-Path $env:TEMP "reader-gui-smoke-$runId"
$profileRoot = Join-Path $testRoot "profile"
$sampleRoot = Join-Path $testRoot "samples"
$tempRoot = Join-Path $testRoot "temp"
$batchLog = Join-Path $testRoot "batches.jsonl"
$namespace = "gui-smoke-$runId"
$lockPath = Join-Path $tempRoot "reader-single-instance-locks\Reader.SingleInstance.v1.$namespace.lock"
$primary = $null
$secondaries = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$smokeSucceeded = $false
$smokeError = $null
$cleanupFailures = [System.Collections.Generic.List[string]]::new()
$verifiedBatches = @()

function Wait-Until {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Condition,
        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        if (& $Condition) {
            return
        }
        Start-Sleep -Milliseconds 100
    } while ([DateTime]::UtcNow -lt $deadline)
    throw $FailureMessage
}

function Get-ReaderProcesses {
    @(Get-CimInstance Win32_Process | Where-Object {
        $_.ExecutablePath -and
        [string]::Equals($_.ExecutablePath, $resolvedExe, [StringComparison]::OrdinalIgnoreCase)
    })
}

function Test-LoggedBatch {
    param(
        [int]$Index,
        [string[]]$Expected
    )

    if (-not (Test-Path -LiteralPath $batchLog)) {
        return $false
    }
    $lines = @(Get-Content -LiteralPath $batchLog -Encoding UTF8)
    if ($lines.Count -le $Index) {
        return $false
    }
    try {
        $decoded = $lines[$Index] | ConvertFrom-Json
        $actual = @($decoded)
    } catch {
        return $false
    }
    if ($actual.Count -ne $Expected.Count) {
        return $false
    }
    for ($itemIndex = 0; $itemIndex -lt $Expected.Count; $itemIndex++) {
        if ($actual[$itemIndex] -cne $Expected[$itemIndex]) {
            return $false
        }
    }
    return $true
}

function Get-TrackedProcessIds {
    param([int[]]$RootProcessIds)

    $snapshot = @(Get-CimInstance Win32_Process)
    $pending = @($RootProcessIds)
    $tracked = [System.Collections.Generic.List[int]]::new()
    while ($pending.Count -gt 0) {
        $parent = $pending[0]
        if ($pending.Count -eq 1) {
            $pending = @()
        } else {
            $pending = @($pending[1..($pending.Count - 1)])
        }
        if (-not $tracked.Contains($parent)) {
            $tracked.Add($parent)
            $pending += @(
                $snapshot |
                    Where-Object ParentProcessId -eq $parent |
                    ForEach-Object ProcessId
            )
        }
    }
    return @($tracked)
}

function Stop-SmokeProcesses {
    $rootIds = [System.Collections.Generic.List[int]]::new()
    if ($null -ne $primary) {
        $rootIds.Add($primary.Id)
    }
    foreach ($secondary in $secondaries) {
        $rootIds.Add($secondary.Id)
    }
    foreach ($process in @(Get-ReaderProcesses)) {
        if ($process.ProcessId -notin $baselineReaderProcessIds) {
            $rootIds.Add([int]$process.ProcessId)
        }
    }
    $trackedIds = @(
        Get-TrackedProcessIds -RootProcessIds @($rootIds | Select-Object -Unique)
    )
    $trackedIds = @(
        $trackedIds |
            Where-Object { $_ -notin $baselineReaderProcessIds } |
            Select-Object -Unique
    )

    foreach ($processId in $trackedIds) {
        Stop-Process -Id $processId -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 250
    foreach ($processId in $trackedIds) {
        if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    }
    foreach ($process in @(@($primary) + @($secondaries))) {
        if ($null -ne $process) {
            [void]$process.WaitForExit(5000)
        }
    }
    Wait-Until -FailureMessage "Smoke process tree did not exit" -Condition {
        @(
            $trackedIds |
                Where-Object {
                    $null -ne (Get-Process -Id $_ -ErrorAction SilentlyContinue)
                }
        ).Count -eq 0
    }
}

function Remove-SmokeRoot {
    $lastError = $null
    for ($attempt = 1; $attempt -le 10; $attempt++) {
        try {
            if (Test-Path -LiteralPath $testRoot) {
                Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction Stop
            }
            if (-not (Test-Path -LiteralPath $testRoot)) {
                return
            }
        } catch {
            $lastError = $_
        }
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
        Start-Sleep -Milliseconds 250
    }
    $detail = if ($null -ne $lastError) { ": $lastError" } else { "" }
    throw "Failed to remove smoke test root $testRoot$detail"
}

function Get-NewReaderProcesses {
    @(
        Get-ReaderProcesses |
            Where-Object ProcessId -NotIn $baselineReaderProcessIds
    )
}

$baselineReaderProcessIds = @(
    Get-ReaderProcesses | ForEach-Object { [int]$_.ProcessId }
)
$savedEnvironment = @{}
$environmentOverrides = @{
    "READER_SKIP_SHELL_INTEGRATION" = "1"
    "READER_IPC_NAMESPACE" = $namespace
    "READER_SMOKE_BATCH_LOG" = $batchLog
    "QTWEBENGINE_CHROMIUM_FLAGS" = "--user-data-dir=`"$profileRoot\chromium`""
    "USERPROFILE" = $profileRoot
    "APPDATA" = (Join-Path $profileRoot "AppData\Roaming")
    "LOCALAPPDATA" = (Join-Path $profileRoot "AppData\Local")
    "TEMP" = $tempRoot
    "TMP" = $tempRoot
}
foreach ($name in $environmentOverrides.Keys) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
}

try {
    New-Item -ItemType Directory -Force $sampleRoot | Out-Null
    New-Item -ItemType Directory -Force $tempRoot | Out-Null
    New-Item -ItemType Directory -Force $environmentOverrides.APPDATA | Out-Null
    New-Item -ItemType Directory -Force $environmentOverrides.LOCALAPPDATA | Out-Null
    New-Item -ItemType File -Force $batchLog | Out-Null
    $batchOne = @(
        (Join-Path $sampleRoot "batch-one-a.md"),
        (Join-Path $sampleRoot "batch-one-b.md")
    )
    $batchTwo = @(
        (Join-Path $sampleRoot "batch-two-a.md"),
        (Join-Path $sampleRoot "batch-two-b.md")
    )
    foreach ($path in @($batchOne + $batchTwo)) {
        Set-Content -Path $path -Value "# $([IO.Path]::GetFileNameWithoutExtension($path))" -Encoding UTF8
    }

    foreach ($name in $environmentOverrides.Keys) {
        [Environment]::SetEnvironmentVariable($name, $environmentOverrides[$name], "Process")
    }

    $primary = Start-Process -FilePath $resolvedExe -ArgumentList $batchOne -PassThru
    Wait-Until -FailureMessage "Primary Reader process exited or did not show a window" -Condition {
        $process = Get-Process -Id $primary.Id -ErrorAction SilentlyContinue
        $process -and -not $process.HasExited -and $process.MainWindowHandle -ne 0
    }
    Wait-Until -FailureMessage "Expected one new primary Reader.exe process" -Condition {
        $newReaders = @(Get-NewReaderProcesses)
        $newReaders.Count -eq 1 -and $newReaders[0].ProcessId -eq $primary.Id
    }
    Wait-Until -FailureMessage "Initial two-path batch was not logged exactly" -Condition {
        (Test-LoggedBatch -Index 0 -Expected $batchOne)
    }

    $secondary = Start-Process -FilePath $resolvedExe -ArgumentList $batchTwo -PassThru
    $secondaries.Add($secondary)
    Wait-Until -FailureMessage "Second launch did not forward and exit" -Condition {
        $secondary.HasExited
    }
    if ($secondary.ExitCode -ne 0) {
        throw "Second Reader launch exited with code $($secondary.ExitCode)"
    }
    Wait-Until -FailureMessage "Forwarded two-path batch was not logged exactly" -Condition {
        (Test-LoggedBatch -Index 1 -Expected $batchTwo)
    }
    $loggedLines = @(Get-Content -LiteralPath $batchLog -Encoding UTF8)
    if ($loggedLines.Count -ne 2) {
        throw "Expected exactly two telemetry batches, got $($loggedLines.Count)"
    }
    $verifiedBatches = $loggedLines
    Wait-Until -FailureMessage "Primary Reader process did not survive forwarding" -Condition {
        $process = Get-Process -Id $primary.Id -ErrorAction SilentlyContinue
        $process -and -not $process.HasExited -and $process.MainWindowHandle -ne 0
    }
    $newReaderProcesses = @(Get-NewReaderProcesses)
    if (
        $newReaderProcesses.Count -ne 1 -or
        $newReaderProcesses[0].ProcessId -ne $primary.Id
    ) {
        throw "Expected exactly one original primary Reader.exe after forwarding"
    }
    $smokeSucceeded = $true
} catch {
    $smokeError = $_
} finally {
    try {
        if (
            -not $smokeSucceeded -and
            (Test-Path -LiteralPath $batchLog)
        ) {
            $diagnosticBatches = Get-Content -LiteralPath $batchLog -Raw -Encoding UTF8
            Write-Warning "Smoke telemetry before cleanup: $diagnosticBatches"
        }
    } catch {
        $cleanupFailures.Add("telemetry diagnostics: $_")
    }
    try {
        Stop-SmokeProcesses
    } catch {
        $cleanupFailures.Add("process cleanup: $_")
    }
    foreach ($name in $environmentOverrides.Keys) {
        try {
            [Environment]::SetEnvironmentVariable(
                $name,
                $savedEnvironment[$name],
                "Process"
            )
        } catch {
            $cleanupFailures.Add("restore environment $name`: $_")
        }
    }
    try {
        if (Test-Path -LiteralPath $lockPath) {
            Remove-Item -LiteralPath $lockPath -Force -ErrorAction Stop
        }
    } catch {
        $cleanupFailures.Add("namespace lock cleanup: $_")
    }
    try {
        Remove-SmokeRoot
    } catch {
        $cleanupFailures.Add("test root cleanup: $_")
    }
}

$resolvedFailure = Resolve-SmokeFailure `
    -SmokeError $smokeError `
    -CleanupFailures @($cleanupFailures)
if ($null -ne $resolvedFailure) {
    throw $resolvedFailure
}

if ($smokeSucceeded) {
    Write-Host "Reader GUI smoke batch 1: $($verifiedBatches[0])"
    Write-Host "Reader GUI smoke batch 2: $($verifiedBatches[1])"
    Write-Host "Reader GUI smoke passed: primary PID $($primary.Id), exact two 2-file batches"
}
