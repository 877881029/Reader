[CmdletBinding()]
param(
    [switch]$Release,
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

$pythonPrefix = @()
if ([string]::IsNullOrWhiteSpace($Python)) {
    if (-not [string]::IsNullOrWhiteSpace($env:READER_PYTHON)) {
        $Python = $env:READER_PYTHON
    } elseif (Test-Path ".venv\Scripts\python.exe" -PathType Leaf) {
        $Python = (Resolve-Path ".venv\Scripts\python.exe").Path
    } else {
        $Python = (Get-Command py.exe -ErrorAction Stop).Source
        $pythonPrefix = @("-3.12")
    }
}

$npm = Get-Command npm.cmd -ErrorAction Stop
function Invoke-Npm([string]$Arguments) {
    $process = Start-Process -FilePath $env:ComSpec `
        -ArgumentList @("/d", "/s", "/c", "call `"$($npm.Source)`" $Arguments") `
        -WorkingDirectory $Root -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -ne 0) {
        throw "npm $Arguments failed (exit $($process.ExitCode))"
    }
}

function Write-WebBundleManifest([string]$BundlePath) {
    $assetFiles = Get-ChildItem $BundlePath -File -Recurse |
        Where-Object Name -ne "manifest.sha256"
    $bundleRoot = (Resolve-Path $BundlePath).Path.TrimEnd("\")
    $relativePaths = [string[]]@(
        foreach ($file in $assetFiles) {
            $file.FullName.Substring($bundleRoot.Length + 1).Replace("\", "/")
        }
    )
    [Array]::Sort($relativePaths, [StringComparer]::Ordinal)
    $lines = foreach ($relative in $relativePaths) {
        $path = Join-Path $BundlePath $relative
        "$((Get-FileHash $path -Algorithm SHA256).Hash.ToLower())  $relative"
    }
    $manifestPath = Join-Path $BundlePath "manifest.sha256"
    $content = (($lines -join "`n") + "`n")
    [System.IO.File]::WriteAllBytes(
        $manifestPath,
        [System.Text.Encoding]::ASCII.GetBytes($content)
    )
}

Invoke-Npm "ci --prefix web\pptx-viewer"
Invoke-Npm "test --prefix web\pptx-viewer"
Invoke-Npm "run typecheck --prefix web\pptx-viewer"
Invoke-Npm "run build --prefix web\pptx-viewer"
Invoke-Npm "ci --prefix web\md-viewer"
Invoke-Npm "test --prefix web\md-viewer"
Invoke-Npm "run typecheck --prefix web\md-viewer"
Invoke-Npm "run build --prefix web\md-viewer"

$PptxBundlePath = Join-Path $Root "assets\pptx-viewer"
$PptxNoticePath = Join-Path $Root "web\pptx-viewer\THIRD_PARTY_NOTICES.txt"
Copy-Item $PptxNoticePath `
    (Join-Path $PptxBundlePath "THIRD_PARTY_NOTICES.txt") -Force
Write-WebBundleManifest -BundlePath $PptxBundlePath

Write-Host "Running Python tests with $Python"
& $Python @pythonPrefix -m pytest
if ($LASTEXITCODE -ne 0) {
    throw "Python tests failed (exit $LASTEXITCODE)"
}

if ($Release) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass `
        -File (Join-Path $PSScriptRoot "build_windows.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "Frozen build failed (exit $LASTEXITCODE)"
    }

    $readerExe = Join-Path $Root "dist\Reader\Reader.exe"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass `
        -File (Join-Path $PSScriptRoot "smoke_windows.ps1") `
        -ReaderExe $readerExe
    if ($LASTEXITCODE -ne 0) {
        throw "Frozen smoke failed (exit $LASTEXITCODE)"
    }
}

$verificationMessage = if ($Release) {
    "Reader release verification passed"
} else {
    "Reader fast verification passed"
}
Write-Host $verificationMessage
