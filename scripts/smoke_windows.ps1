[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ReaderExe,
    [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$resolvedExe = (Resolve-Path $ReaderExe).Path
$runId = [Guid]::NewGuid().ToString("N")
$testRoot = Join-Path $env:TEMP "reader-gui-smoke-$runId"
$profileRoot = Join-Path $testRoot "profile"
$sampleRoot = Join-Path $testRoot "samples"
$primary = $null

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

function Stop-ProcessTree {
    param([int]$RootProcessId)

    $all = @(Get-CimInstance Win32_Process)
    $pending = @($RootProcessId)
    $tree = [System.Collections.Generic.List[int]]::new()
    while ($pending.Count -gt 0) {
        $parent = $pending[0]
        if ($pending.Count -eq 1) {
            $pending = @()
        } else {
            $pending = @($pending[1..($pending.Count - 1)])
        }
        if (-not $tree.Contains($parent)) {
            $tree.Add($parent)
            $pending += @($all | Where-Object ParentProcessId -eq $parent | ForEach-Object ProcessId)
        }
    }
    foreach ($processId in @($tree | Sort-Object -Descending)) {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
}

$savedEnvironment = @{}
$environmentOverrides = @{
    "READER_SKIP_SHELL_INTEGRATION" = "1"
    "READER_IPC_NAMESPACE" = "gui-smoke-$runId"
    "QTWEBENGINE_CHROMIUM_FLAGS" = "--user-data-dir=`"$profileRoot\chromium`""
    "USERPROFILE" = $profileRoot
    "APPDATA" = (Join-Path $profileRoot "AppData\Roaming")
    "LOCALAPPDATA" = (Join-Path $profileRoot "AppData\Local")
}

try {
    New-Item -ItemType Directory -Force $sampleRoot | Out-Null
    New-Item -ItemType Directory -Force $environmentOverrides.APPDATA | Out-Null
    New-Item -ItemType Directory -Force $environmentOverrides.LOCALAPPDATA | Out-Null
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
        $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
        [Environment]::SetEnvironmentVariable($name, $environmentOverrides[$name], "Process")
    }

    $primary = Start-Process -FilePath $resolvedExe -ArgumentList $batchOne -PassThru
    Wait-Until -FailureMessage "Primary Reader process exited or did not show a window" -Condition {
        $process = Get-Process -Id $primary.Id -ErrorAction SilentlyContinue
        $process -and -not $process.HasExited -and $process.MainWindowHandle -ne 0
    }
    Wait-Until -FailureMessage "Expected one primary Reader.exe process" -Condition {
        @(Get-ReaderProcesses).Count -eq 1
    }

    $secondary = Start-Process -FilePath $resolvedExe -ArgumentList $batchTwo -PassThru
    Wait-Until -FailureMessage "Second launch did not forward and exit" -Condition {
        $secondary.HasExited
    }
    if ($secondary.ExitCode -ne 0) {
        throw "Second Reader launch exited with code $($secondary.ExitCode)"
    }
    Wait-Until -FailureMessage "Primary Reader process did not survive forwarding" -Condition {
        $process = Get-Process -Id $primary.Id -ErrorAction SilentlyContinue
        $process -and -not $process.HasExited -and $process.MainWindowHandle -ne 0
    }
    $readerProcesses = @(Get-ReaderProcesses)
    if ($readerProcesses.Count -ne 1 -or $readerProcesses[0].ProcessId -ne $primary.Id) {
        throw "Expected exactly one original primary Reader.exe after forwarding"
    }

    Write-Host "Reader GUI smoke passed: primary PID $($primary.Id), two 2-file batches"
} finally {
    if ($null -ne $primary) {
        Stop-ProcessTree -RootProcessId $primary.Id
    }
    foreach ($name in $environmentOverrides.Keys) {
        [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], "Process")
    }
    Remove-Item -Recurse -Force $testRoot -ErrorAction SilentlyContinue
}
