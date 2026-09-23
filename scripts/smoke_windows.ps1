[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ReaderExe,
    [int]$TimeoutSeconds = 30
)

. (Join-Path $PSScriptRoot "smoke_helpers.ps1")

$ErrorActionPreference = "Stop"
$resolvedExe = (Resolve-Path $ReaderExe).Path
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$fixturePath = (Resolve-Path (
    Join-Path $repoRoot "tests\fixtures\pptx\visual-elements.pptx"
)).Path
$markdownFixturePath = (Resolve-Path (
    Join-Path $repoRoot "tests\fixtures\md\visual-document.md"
)).Path
$runId = [Guid]::NewGuid().ToString("N")
$visualRoot = Join-Path $env:TEMP "reader-visual-smoke-$runId"
$visualProfileRoot = Join-Path $visualRoot "profile"
$visualTempRoot = Join-Path $visualRoot "temp"
$visualLog = Join-Path $visualRoot "visual.jsonl"
$visualNamespace = "visual-smoke-$runId"
$visualLockPath = Join-Path $visualTempRoot (
    "reader-single-instance-locks\Reader.SingleInstance.v1.$visualNamespace.lock"
)
$markdownRoot = Join-Path $env:TEMP "reader-markdown-smoke-$runId"
$markdownProfileRoot = Join-Path $markdownRoot "profile"
$markdownTempRoot = Join-Path $markdownRoot "temp"
$markdownLog = Join-Path $markdownRoot "visual.jsonl"
$markdownNamespace = "markdown-smoke-$runId"
$markdownLockPath = Join-Path $markdownTempRoot (
    "reader-single-instance-locks\Reader.SingleInstance.v1.$markdownNamespace.lock"
)
$textRoot = Join-Path $env:TEMP "reader-text-smoke-$runId"
$textProfileRoot = Join-Path $textRoot "profile"
$textTempRoot = Join-Path $textRoot "temp"
$textFixturePath = Join-Path $textRoot "sample.txt"
$textLog = Join-Path $textRoot "document.jsonl"
$textNamespace = "text-smoke-$runId"
$textLockPath = Join-Path $textTempRoot (
    "reader-single-instance-locks\Reader.SingleInstance.v1.$textNamespace.lock"
)
$cppRoot = Join-Path $env:TEMP "reader-cpp-smoke-$runId"
$cppProfileRoot = Join-Path $cppRoot "profile"
$cppTempRoot = Join-Path $cppRoot "temp"
$cppFixturePath = Join-Path $cppRoot "sample.cpp"
$hppFixturePath = Join-Path $cppRoot "sample.hpp"
$ccFixturePath = Join-Path $cppRoot "sample.cc"
$cxxFixturePath = Join-Path $cppRoot "sample.cxx"
$hhFixturePath = Join-Path $cppRoot "sample.hh"
$hxxFixturePath = Join-Path $cppRoot "sample.hxx"
$inlFixturePath = Join-Path $cppRoot "sample.inl"
$ippFixturePath = Join-Path $cppRoot "sample.ipp"
$cppLog = Join-Path $cppRoot "document.jsonl"
$cppNamespace = "cpp-smoke-$runId"
$cppLockPath = Join-Path $cppTempRoot (
    "reader-single-instance-locks\Reader.SingleInstance.v1.$cppNamespace.lock"
)
$ipcRoot = Join-Path $env:TEMP "reader-gui-smoke-$runId"
$ipcProfileRoot = Join-Path $ipcRoot "profile"
$sampleRoot = Join-Path $ipcRoot "samples"
$ipcTempRoot = Join-Path $ipcRoot "temp"
$batchLog = Join-Path $ipcRoot "batches.jsonl"
$ipcNamespace = "gui-smoke-$runId"
$ipcLockPath = Join-Path $ipcTempRoot (
    "reader-single-instance-locks\Reader.SingleInstance.v1.$ipcNamespace.lock"
)
$visualProcess = $null
$markdownProcess = $null
$textProcess = $null
$cppProcess = $null
$ipcPrimary = $null
$secondaries = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$smokeSucceeded = $false
$smokeError = $null
$cleanupFailures = [System.Collections.Generic.List[string]]::new()
$verifiedVisual = $null
$verifiedMarkdown = $null
$verifiedText = $null
$verifiedCpp = $null
$verifiedHpp = $null
$verifiedCc = $null
$verifiedCxx = $null
$verifiedHh = $null
$verifiedHxx = $null
$verifiedInl = $null
$verifiedIpp = $null
$verifiedBatches = @()
$textPreviewStatus = -join @(
    [char]0x6587
    [char]0x672C
    [char]0x9884
    [char]0x89C8
)
$codePreviewStatus = -join @(
    [char]0x4EE3
    [char]0x7801
    [char]0x9884
    [char]0x89C8
)

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
        [string]::Equals(
            $_.ExecutablePath,
            $resolvedExe,
            [StringComparison]::OrdinalIgnoreCase
        )
    })
}

function Get-NewReaderProcesses {
    @(
        Get-ReaderProcesses |
            Where-Object ProcessId -NotIn $baselineReaderProcessIds
    )
}

function Get-TrackedProcessIds {
    param([int[]]$RootProcessIds)

    $snapshot = @(Get-CimInstance Win32_Process)
    $pending = @($RootProcessIds)
    $tracked = [System.Collections.Generic.List[int]]::new()
    while ($pending.Count -gt 0) {
        $parentId = $pending[0]
        if ($pending.Count -eq 1) {
            $pending = @()
        } else {
            $pending = @($pending[1..($pending.Count - 1)])
        }
        if (-not $tracked.Contains($parentId)) {
            $tracked.Add($parentId)
            $pending += @(
                $snapshot |
                    Where-Object ParentProcessId -eq $parentId |
                    ForEach-Object ProcessId
            )
        }
    }
    return @($tracked)
}

function Stop-ProcessTrees {
    param(
        [System.Diagnostics.Process[]]$RootProcesses,
        [string]$FailureMessage
    )

    $rootIds = [System.Collections.Generic.List[int]]::new()
    foreach ($rootProcess in $RootProcesses) {
        if ($null -ne $rootProcess) {
            $rootIds.Add($rootProcess.Id)
        }
    }
    foreach ($readerProcess in @(Get-NewReaderProcesses)) {
        $rootIds.Add([int]$readerProcess.ProcessId)
    }
    $trackedIds = @(
        Get-TrackedProcessIds -RootProcessIds @($rootIds | Select-Object -Unique)
    )
    $trackedIds = @(
        $trackedIds |
            Where-Object { $_ -notin $baselineReaderProcessIds } |
            Select-Object -Unique
    )

    foreach ($trackedId in $trackedIds) {
        Stop-Process -Id $trackedId -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 250
    foreach ($trackedId in $trackedIds) {
        if (Get-Process -Id $trackedId -ErrorAction SilentlyContinue) {
            Stop-Process -Id $trackedId -Force -ErrorAction SilentlyContinue
        }
    }
    foreach ($rootProcess in $RootProcesses) {
        if ($null -ne $rootProcess) {
            [void]$rootProcess.WaitForExit(5000)
        }
    }
    Wait-Until -FailureMessage $FailureMessage -Condition {
        @(
            $trackedIds |
                Where-Object {
                    $null -ne (Get-Process -Id $_ -ErrorAction SilentlyContinue)
                }
        ).Count -eq 0
    }
}

function Stop-VisualProcesses {
    Stop-ProcessTrees `
        -RootProcesses @($visualProcess) `
        -FailureMessage "Visual smoke process tree did not exit"
}

function Stop-IpcProcesses {
    Stop-ProcessTrees `
        -RootProcesses @(@($ipcPrimary) + @($secondaries)) `
        -FailureMessage "IPC smoke process tree did not exit"
}

function Stop-MarkdownProcesses {
    Stop-ProcessTrees `
        -RootProcesses @($markdownProcess) `
        -FailureMessage "Markdown smoke process tree did not exit"
}

function Stop-TextProcesses {
    Stop-ProcessTrees `
        -RootProcesses @($textProcess) `
        -FailureMessage "TXT smoke process tree did not exit"
}

function Stop-CppProcesses {
    Stop-ProcessTrees `
        -RootProcesses @($cppProcess) `
        -FailureMessage "C++ smoke process tree did not exit"
}

function Remove-IsolationRoot {
    param([string]$Path)

    $lastError = $null
    for ($attempt = 1; $attempt -le 120; $attempt++) {
        try {
            if (Test-Path -LiteralPath $Path) {
                Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
            }
            if (-not (Test-Path -LiteralPath $Path)) {
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
    throw "Failed to remove smoke test root $Path$detail"
}

function Remove-VisualIsolation {
    if (Test-Path -LiteralPath $visualLockPath) {
        Remove-Item -LiteralPath $visualLockPath -Force -ErrorAction Stop
    }
    Remove-IsolationRoot -Path $visualRoot
}

function Remove-MarkdownIsolation {
    if (Test-Path -LiteralPath $markdownLockPath) {
        Remove-Item -LiteralPath $markdownLockPath -Force -ErrorAction Stop
    }
    Remove-IsolationRoot -Path $markdownRoot
}

function Remove-TextIsolation {
    if (Test-Path -LiteralPath $textLockPath) {
        Remove-Item -LiteralPath $textLockPath -Force -ErrorAction Stop
    }
    Remove-IsolationRoot -Path $textRoot
}

function Remove-CppIsolation {
    if (Test-Path -LiteralPath $cppLockPath) {
        Remove-Item -LiteralPath $cppLockPath -Force -ErrorAction Stop
    }
    Remove-IsolationRoot -Path $cppRoot
}

function Set-SmokeEnvironment {
    param(
        [string]$Namespace,
        [string]$ProfileRoot,
        [string]$LocalAppDataRoot,
        [string]$TempRoot,
        [AllowEmptyString()]
        [string]$BatchLogPath,
        [AllowEmptyString()]
        [string]$VisualLogPath,
        [AllowEmptyString()]
        [string]$MarkdownVisual = ""
    )

    $values = @{
        "READER_SKIP_SHELL_INTEGRATION" = "1"
        "READER_IPC_NAMESPACE" = $Namespace
        "READER_SMOKE_BATCH_LOG" = $BatchLogPath
        "READER_SMOKE_VISUAL_LOG" = $VisualLogPath
        "READER_SMOKE_MD_VISUAL" = $MarkdownVisual
        "QTWEBENGINE_CHROMIUM_FLAGS" = "--user-data-dir=`"$ProfileRoot\chromium`""
        "USERPROFILE" = $ProfileRoot
        "APPDATA" = (Join-Path $ProfileRoot "AppData\Roaming")
        "LOCALAPPDATA" = $LocalAppDataRoot
        "TEMP" = $TempRoot
        "TMP" = $TempRoot
    }
    foreach ($name in $values.Keys) {
        [Environment]::SetEnvironmentVariable($name, $values[$name], "Process")
    }
    New-Item -ItemType Directory -Force $TempRoot | Out-Null
    New-Item -ItemType Directory -Force $values.APPDATA | Out-Null
    New-Item -ItemType Directory -Force $values.LOCALAPPDATA | Out-Null
}

function Get-VisualRecord {
    if (-not (Test-Path -LiteralPath $visualLog)) {
        return $null
    }
    foreach ($line in @(Get-Content -LiteralPath $visualLog -Encoding UTF8)) {
        try {
            $record = $line | ConvertFrom-Json
        } catch {
            continue
        }
        if ($record.status -eq "renderer-failure") {
            throw "Frozen visual renderer reported renderer-failure"
        }
        if (
            $record.status -eq "ready" -and
            $record.kind -eq "pptx" -and
            $record.slides -eq 4 -and
            [string]::Equals(
                [string]$record.path,
                $fixturePath,
                [StringComparison]::OrdinalIgnoreCase
            )
        ) {
            return $record
        }
    }
    return $null
}

function Get-MarkdownRecord {
    if (-not (Test-Path -LiteralPath $markdownLog)) {
        return $null
    }
    foreach ($line in @(Get-Content -LiteralPath $markdownLog -Encoding UTF8)) {
        try {
            $record = $line | ConvertFrom-Json
        } catch {
            continue
        }
        if ($record.status -eq "renderer-failure") {
            throw "Frozen markdown renderer reported renderer-failure"
        }
        if (
            $record.status -eq "ready" -and
            $record.kind -eq "markdown" -and
            [string]::Equals(
                [string]$record.path,
                $markdownFixturePath,
                [StringComparison]::OrdinalIgnoreCase
            )
        ) {
            return $record
        }
    }
    return $null
}

function Get-TextRecord {
    if (-not (Test-Path -LiteralPath $textLog)) {
        return $null
    }
    foreach ($line in @(Get-Content -LiteralPath $textLog -Encoding UTF8)) {
        try {
            $record = $line | ConvertFrom-Json
        } catch {
            continue
        }
        if (
            $record.kind -eq "code" -and
            $record.extension -eq ".txt" -and
            $record.status -eq $textPreviewStatus -and
            [string]::Equals(
                [string]$record.path,
                $textFixturePath,
                [StringComparison]::OrdinalIgnoreCase
            )
        ) {
            return $record
        }
    }
    return $null
}

function Get-CppRecord {
    param(
        [string]$Extension,
        [string]$ExpectedPath
    )

    if (-not (Test-Path -LiteralPath $cppLog)) {
        return $null
    }
    foreach ($line in @(Get-Content -LiteralPath $cppLog -Encoding UTF8)) {
        try {
            $record = $line | ConvertFrom-Json
        } catch {
            continue
        }
        if (
            $record.kind -eq "code" -and
            $record.extension -eq $Extension -and
            $record.status -eq $codePreviewStatus -and
            [string]::Equals(
                [string]$record.path,
                $ExpectedPath,
                [StringComparison]::OrdinalIgnoreCase
            )
        ) {
            return $record
        }
    }
    return $null
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

$baselineReaderProcessIds = @(
    Get-ReaderProcesses | ForEach-Object { [int]$_.ProcessId }
)
$environmentNames = @(
    "READER_SKIP_SHELL_INTEGRATION",
    "READER_IPC_NAMESPACE",
    "READER_SMOKE_BATCH_LOG",
    "READER_SMOKE_VISUAL_LOG",
    "READER_SMOKE_MD_VISUAL",
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "TEMP",
    "TMP"
)
$savedEnvironment = @{}
foreach ($name in $environmentNames) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable(
        $name,
        "Process"
    )
}
$hostLocalAppData = $savedEnvironment.LOCALAPPDATA
if ([string]::IsNullOrWhiteSpace($hostLocalAppData)) {
    $hostLocalAppData = [Environment]::GetFolderPath(
        [Environment+SpecialFolder]::LocalApplicationData
    )
}

try {
    # Phase A: frozen visual rendering in its own process and namespace.
    Set-SmokeEnvironment `
        -Namespace $visualNamespace `
        -ProfileRoot $visualProfileRoot `
        -LocalAppDataRoot $hostLocalAppData `
        -TempRoot $visualTempRoot `
        -BatchLogPath "" `
        -VisualLogPath $visualLog
    New-Item -ItemType File -Force $visualLog | Out-Null

    $visualProcess = Start-Process `
        -FilePath $resolvedExe `
        -ArgumentList @($fixturePath) `
        -PassThru
    $visualDeadline = [DateTime]::UtcNow.AddSeconds(60)
    do {
        $runningVisual = Get-Process `
            -Id $visualProcess.Id `
            -ErrorAction SilentlyContinue
        if ($null -eq $runningVisual -or $runningVisual.HasExited) {
            throw "Frozen visual Reader exited before visual-ready"
        }
        $verifiedVisual = Get-VisualRecord
        if ($null -ne $verifiedVisual) {
            break
        }
        Start-Sleep -Milliseconds 100
    } while ([DateTime]::UtcNow -lt $visualDeadline)
    if ($null -eq $verifiedVisual) {
        throw "Frozen visual Reader did not report visual-ready slides=4 within 60 seconds"
    }

    Stop-VisualProcesses
    Remove-VisualIsolation
    $visualProcess = $null

    # Phase B: frozen markdown visual rendering (product default is visual preview).
    Set-SmokeEnvironment `
        -Namespace $markdownNamespace `
        -ProfileRoot $markdownProfileRoot `
        -LocalAppDataRoot $hostLocalAppData `
        -TempRoot $markdownTempRoot `
        -BatchLogPath "" `
        -VisualLogPath $markdownLog `
        -MarkdownVisual "1"
    New-Item -ItemType File -Force $markdownLog | Out-Null

    $markdownProcess = Start-Process `
        -FilePath $resolvedExe `
        -ArgumentList @($markdownFixturePath) `
        -PassThru
    $markdownDeadline = [DateTime]::UtcNow.AddSeconds(60)
    do {
        $runningMarkdown = Get-Process `
            -Id $markdownProcess.Id `
            -ErrorAction SilentlyContinue
        if ($null -eq $runningMarkdown -or $runningMarkdown.HasExited) {
            throw "Frozen markdown Reader exited before format-explicit ready"
        }
        $verifiedMarkdown = Get-MarkdownRecord
        if ($null -ne $verifiedMarkdown) {
            break
        }
        Start-Sleep -Milliseconds 100
    } while ([DateTime]::UtcNow -lt $markdownDeadline)
    if ($null -eq $verifiedMarkdown) {
        throw "Frozen markdown Reader did not report format-explicit ready within 60 seconds"
    }

    Stop-MarkdownProcesses
    Remove-MarkdownIsolation
    $markdownProcess = $null

    # Phase C: frozen TXT rendering in an isolated process and namespace.
    Set-SmokeEnvironment `
        -Namespace $textNamespace `
        -ProfileRoot $textProfileRoot `
        -LocalAppDataRoot (Join-Path $textProfileRoot "AppData\Local") `
        -TempRoot $textTempRoot `
        -BatchLogPath "" `
        -VisualLogPath $textLog
    New-Item -ItemType Directory -Force $textRoot | Out-Null
    Set-Content -LiteralPath $textFixturePath -Value "frozen text ready" -Encoding UTF8
    New-Item -ItemType File -Force $textLog | Out-Null

    $textProcess = Start-Process `
        -FilePath $resolvedExe `
        -ArgumentList @($textFixturePath) `
        -PassThru
    $textDeadline = [DateTime]::UtcNow.AddSeconds(60)
    do {
        $runningText = Get-Process `
            -Id $textProcess.Id `
            -ErrorAction SilentlyContinue
        if ($null -eq $runningText -or $runningText.HasExited) {
            throw "Frozen TXT Reader exited before format-explicit ready"
        }
        $verifiedText = Get-TextRecord
        if ($null -ne $verifiedText) {
            break
        }
        Start-Sleep -Milliseconds 100
    } while ([DateTime]::UtcNow -lt $textDeadline)
    if ($null -eq $verifiedText) {
        throw "Frozen TXT Reader did not report format-explicit ready within 60 seconds"
    }

    Stop-TextProcesses
    Remove-TextIsolation
    $textProcess = $null

    # Phase D: frozen C++ rendering in an isolated process and namespace.
    Set-SmokeEnvironment `
        -Namespace $cppNamespace `
        -ProfileRoot $cppProfileRoot `
        -LocalAppDataRoot (Join-Path $cppProfileRoot "AppData\Local") `
        -TempRoot $cppTempRoot `
        -BatchLogPath "" `
        -VisualLogPath $cppLog
    New-Item -ItemType Directory -Force $cppRoot | Out-Null
    Set-Content `
        -LiteralPath $cppFixturePath `
        -Value "class Reader final {};" `
        -Encoding UTF8
    Set-Content `
        -LiteralPath $hppFixturePath `
        -Value "#pragma once" `
        -Encoding UTF8
    Set-Content `
        -LiteralPath $ccFixturePath `
        -Value "class ReaderCc final {};" `
        -Encoding UTF8
    Set-Content `
        -LiteralPath $cxxFixturePath `
        -Value "class ReaderCxx final {};" `
        -Encoding UTF8
    Set-Content `
        -LiteralPath $hhFixturePath `
        -Value "#pragma once" `
        -Encoding UTF8
    Set-Content `
        -LiteralPath $hxxFixturePath `
        -Value "#pragma once" `
        -Encoding UTF8
    Set-Content `
        -LiteralPath $inlFixturePath `
        -Value "inline int reader_value() { return 1; }" `
        -Encoding UTF8
    Set-Content `
        -LiteralPath $ippFixturePath `
        -Value "template <typename T> T reader_value(T value) { return value; }" `
        -Encoding UTF8
    New-Item -ItemType File -Force $cppLog | Out-Null

    $cppProcess = Start-Process `
        -FilePath $resolvedExe `
        -ArgumentList @(
            $cppFixturePath,
            $hppFixturePath,
            $ccFixturePath,
            $cxxFixturePath,
            $hhFixturePath,
            $hxxFixturePath,
            $inlFixturePath,
            $ippFixturePath
        ) `
        -PassThru
    $cppDeadline = [DateTime]::UtcNow.AddSeconds(60)
    do {
        $runningCpp = Get-Process `
            -Id $cppProcess.Id `
            -ErrorAction SilentlyContinue
        if ($null -eq $runningCpp -or $runningCpp.HasExited) {
            throw "Frozen C++ Reader exited before format-explicit ready"
        }
        $verifiedCpp = Get-CppRecord `
            -Extension ".cpp" `
            -ExpectedPath $cppFixturePath
        $verifiedHpp = Get-CppRecord `
            -Extension ".hpp" `
            -ExpectedPath $hppFixturePath
        $verifiedCc = Get-CppRecord `
            -Extension ".cc" `
            -ExpectedPath $ccFixturePath
        $verifiedCxx = Get-CppRecord `
            -Extension ".cxx" `
            -ExpectedPath $cxxFixturePath
        $verifiedHh = Get-CppRecord `
            -Extension ".hh" `
            -ExpectedPath $hhFixturePath
        $verifiedHxx = Get-CppRecord `
            -Extension ".hxx" `
            -ExpectedPath $hxxFixturePath
        $verifiedInl = Get-CppRecord `
            -Extension ".inl" `
            -ExpectedPath $inlFixturePath
        $verifiedIpp = Get-CppRecord `
            -Extension ".ipp" `
            -ExpectedPath $ippFixturePath
        if (
            $null -ne $verifiedCpp -and
            $null -ne $verifiedHpp -and
            $null -ne $verifiedCc -and
            $null -ne $verifiedCxx -and
            $null -ne $verifiedHh -and
            $null -ne $verifiedHxx -and
            $null -ne $verifiedInl -and
            $null -ne $verifiedIpp
        ) {
            break
        }
        Start-Sleep -Milliseconds 100
    } while ([DateTime]::UtcNow -lt $cppDeadline)
    if (
        $null -eq $verifiedCpp -or
        $null -eq $verifiedHpp -or
        $null -eq $verifiedCc -or
        $null -eq $verifiedCxx -or
        $null -eq $verifiedHh -or
        $null -eq $verifiedHxx -or
        $null -eq $verifiedInl -or
        $null -eq $verifiedIpp
    ) {
        throw "Frozen C++ Reader did not report all format-explicit ready events within 60 seconds"
    }

    Stop-CppProcesses
    Remove-CppIsolation
    $cppProcess = $null

    # Phase E: existing two-batch IPC smoke with a new primary.
    Set-SmokeEnvironment `
        -Namespace $ipcNamespace `
        -ProfileRoot $ipcProfileRoot `
        -LocalAppDataRoot (Join-Path $ipcProfileRoot "AppData\Local") `
        -TempRoot $ipcTempRoot `
        -BatchLogPath $batchLog `
        -VisualLogPath ""
    New-Item -ItemType Directory -Force $sampleRoot | Out-Null
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
        Set-Content `
            -Path $path `
            -Value "# $([IO.Path]::GetFileNameWithoutExtension($path))" `
            -Encoding UTF8
    }

    $ipcPrimary = Start-Process `
        -FilePath $resolvedExe `
        -ArgumentList $batchOne `
        -PassThru
    Wait-Until -FailureMessage (
        "Primary Reader process exited or did not show a window"
    ) -Condition {
        $process = Get-Process -Id $ipcPrimary.Id -ErrorAction SilentlyContinue
        $process -and -not $process.HasExited -and $process.MainWindowHandle -ne 0
    }
    Wait-Until -FailureMessage "Expected one new primary Reader.exe process" -Condition {
        $newReaders = @(Get-NewReaderProcesses)
        $newReaders.Count -eq 1 -and
            $newReaders[0].ProcessId -eq $ipcPrimary.Id
    }
    Wait-Until -FailureMessage "Initial two-path batch was not logged exactly" -Condition {
        Test-LoggedBatch -Index 0 -Expected $batchOne
    }

    $secondary = Start-Process `
        -FilePath $resolvedExe `
        -ArgumentList $batchTwo `
        -PassThru
    $secondaries.Add($secondary)
    Wait-Until -FailureMessage "Second launch did not forward and exit" -Condition {
        $secondary.HasExited
    }
    if ($secondary.ExitCode -ne 0) {
        throw "Second Reader launch exited with code $($secondary.ExitCode)"
    }
    Wait-Until -FailureMessage "Forwarded two-path batch was not logged exactly" -Condition {
        Test-LoggedBatch -Index 1 -Expected $batchTwo
    }
    $loggedLines = @(Get-Content -LiteralPath $batchLog -Encoding UTF8)
    if ($loggedLines.Count -ne 2) {
        throw "Expected exactly two telemetry batches, got $($loggedLines.Count)"
    }
    $verifiedBatches = $loggedLines
    Wait-Until -FailureMessage "Primary Reader process did not survive forwarding" -Condition {
        $process = Get-Process -Id $ipcPrimary.Id -ErrorAction SilentlyContinue
        $process -and -not $process.HasExited -and $process.MainWindowHandle -ne 0
    }
    $newReaderProcesses = @(Get-NewReaderProcesses)
    if (
        $newReaderProcesses.Count -ne 1 -or
        $newReaderProcesses[0].ProcessId -ne $ipcPrimary.Id
    ) {
        throw "Expected exactly one original primary Reader.exe after forwarding"
    }
    $smokeSucceeded = $true
} catch {
    $smokeError = $_
} finally {
    try {
        if (-not $smokeSucceeded -and (Test-Path -LiteralPath $textLog)) {
            $textDiagnostic = Get-Content `
                -LiteralPath $textLog `
                -Raw `
                -Encoding UTF8
            Write-Warning "TXT smoke telemetry before cleanup: $textDiagnostic"
        }
    } catch {
        $cleanupFailures.Add("TXT telemetry diagnostics: $_")
    }
    try {
        if (-not $smokeSucceeded -and (Test-Path -LiteralPath $cppLog)) {
            $cppDiagnostic = Get-Content `
                -LiteralPath $cppLog `
                -Raw `
                -Encoding UTF8
            Write-Warning "C++ smoke telemetry before cleanup: $cppDiagnostic"
        }
    } catch {
        $cleanupFailures.Add("C++ telemetry diagnostics: $_")
    }
    try {
        if (-not $smokeSucceeded -and (Test-Path -LiteralPath $markdownLog)) {
            $markdownDiagnostic = Get-Content `
                -LiteralPath $markdownLog `
                -Raw `
                -Encoding UTF8
            Write-Warning "Markdown smoke telemetry before cleanup: $markdownDiagnostic"
        }
    } catch {
        $cleanupFailures.Add("markdown telemetry diagnostics: $_")
    }
    try {
        if (-not $smokeSucceeded -and (Test-Path -LiteralPath $visualLog)) {
            $visualDiagnostic = Get-Content `
                -LiteralPath $visualLog `
                -Raw `
                -Encoding UTF8
            Write-Warning "Visual smoke telemetry before cleanup: $visualDiagnostic"
        }
        if (-not $smokeSucceeded -and (Test-Path -LiteralPath $batchLog)) {
            $batchDiagnostic = Get-Content `
                -LiteralPath $batchLog `
                -Raw `
                -Encoding UTF8
            Write-Warning "IPC smoke telemetry before cleanup: $batchDiagnostic"
        }
    } catch {
        $cleanupFailures.Add("telemetry diagnostics: $_")
    }
    try {
        Stop-VisualProcesses
    } catch {
        $cleanupFailures.Add("visual process cleanup: $_")
    }
    try {
        Stop-IpcProcesses
    } catch {
        $cleanupFailures.Add("IPC process cleanup: $_")
    }
    try {
        Stop-MarkdownProcesses
    } catch {
        $cleanupFailures.Add("markdown process cleanup: $_")
    }
    try {
        Stop-TextProcesses
    } catch {
        $cleanupFailures.Add("TXT process cleanup: $_")
    }
    try {
        Stop-CppProcesses
    } catch {
        $cleanupFailures.Add("C++ process cleanup: $_")
    }
    foreach ($name in $environmentNames) {
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
    foreach ($lockPath in @(
        $visualLockPath,
        $markdownLockPath,
        $textLockPath,
        $cppLockPath,
        $ipcLockPath
    )) {
        try {
            if (Test-Path -LiteralPath $lockPath) {
                Remove-Item -LiteralPath $lockPath -Force -ErrorAction Stop
            }
        } catch {
            $cleanupFailures.Add("namespace lock cleanup $lockPath`: $_")
        }
    }
    foreach ($rootPath in @(
        $visualRoot,
        $markdownRoot,
        $textRoot,
        $cppRoot,
        $ipcRoot
    )) {
        try {
            Remove-IsolationRoot -Path $rootPath
        } catch {
            $cleanupFailures.Add("test root cleanup $rootPath`: $_")
        }
    }
}

$resolvedFailure = Resolve-SmokeFailure `
    -SmokeError $smokeError `
    -CleanupFailures @($cleanupFailures)
if ($null -ne $resolvedFailure) {
    throw $resolvedFailure
}

if ($smokeSucceeded) {
    Write-Host "Reader visual smoke: $($verifiedVisual | ConvertTo-Json -Compress)"
    Write-Host "Reader markdown smoke: $($verifiedMarkdown | ConvertTo-Json -Compress)"
    Write-Host "Reader TXT smoke: $($verifiedText | ConvertTo-Json -Compress)"
    Write-Host (
        "Reader C++ smoke: cpp=" +
        "$($verifiedCpp | ConvertTo-Json -Compress) hpp=" +
        "$($verifiedHpp | ConvertTo-Json -Compress) cc=" +
        "$($verifiedCc | ConvertTo-Json -Compress) cxx=" +
        "$($verifiedCxx | ConvertTo-Json -Compress) hh=" +
        "$($verifiedHh | ConvertTo-Json -Compress) hxx=" +
        "$($verifiedHxx | ConvertTo-Json -Compress) inl=" +
        "$($verifiedInl | ConvertTo-Json -Compress) ipp=" +
        "$($verifiedIpp | ConvertTo-Json -Compress)"
    )
    Write-Host "Reader GUI smoke batch 1: $($verifiedBatches[0])"
    Write-Host "Reader GUI smoke batch 2: $($verifiedBatches[1])"
    Write-Host (
        "Reader GUI smoke passed: IPC primary PID $($ipcPrimary.Id), " +
        "visual-ready slides=4, markdown-ready kind=markdown, " +
        "TXT-ready kind=code extension=.txt, " +
        "C++-ready extensions=.cpp,.hpp,.cc,.cxx,.hh,.hxx,.inl,.ipp, " +
        "exact two 2-file batches"
    )
}
