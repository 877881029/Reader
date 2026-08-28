$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$npm = Get-Command npm.cmd -ErrorAction Stop
$npmDir = Split-Path -Parent $npm.Source
$npmRelativeNode = Join-Path $npmDir "node.exe"
if (Test-Path $npmRelativeNode -PathType Leaf) {
    $nodePath = (Resolve-Path $npmRelativeNode).Path
} else {
    $nodePath = (Get-Command node.exe -ErrorAction Stop).Source
}
Write-Host "Using Node.js from $nodePath"
$nodeVersion = & $nodePath --version
$nodeExitCode = $LASTEXITCODE
if ($nodeExitCode -ne 0 -or $nodeVersion -notmatch "^v(\d+)\.") {
    throw "Node.js 18+ is required at $nodePath (version check failed)"
}
$major = [int]$Matches[1]
if ($major -lt 18) {
    throw "Node.js 18+ is required at $nodePath (found $nodeVersion)"
}

function Invoke-Npm([string]$Arguments) {
    $process = Start-Process -FilePath $env:ComSpec `
        -ArgumentList @("/d", "/s", "/c", "call `"$($npm.Source)`" $Arguments") `
        -WorkingDirectory $Root -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -ne 0) {
        throw "npm $Arguments failed (exit $($process.ExitCode))"
    }
}

function Test-WebBundleManifest(
    [string]$ManifestPath,
    [string]$BundlePath,
    [string]$MismatchLabel
) {
    $entriesValidated = 0
    foreach ($line in Get-Content $ManifestPath) {
        if (
            [string]::IsNullOrWhiteSpace($line) -or
            $line -notmatch "^[0-9a-f]{64}  .+$"
        ) {
            throw "Invalid web bundle manifest entry: $line"
        }
        $hash, $relative = $line -split "  ", 2
        $actual = (
            Get-FileHash (Join-Path $BundlePath $relative) -Algorithm SHA256
        ).Hash.ToLower()
        if ($actual -ne $hash) {
            throw "$MismatchLabel`: $relative"
        }
        $entriesValidated += 1
    }
    if ($entriesValidated -eq 0) {
        throw "Web bundle manifest has no entries: $ManifestPath"
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
    $lines | Set-Content $manifestPath -Encoding ascii
    return $manifestPath
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
if (-not (Test-Path (Join-Path $PptxBundlePath "index.html"))) {
    throw "PPTX viewer build did not produce index.html"
}
Copy-Item $PptxNoticePath (Join-Path $PptxBundlePath "THIRD_PARTY_NOTICES.txt") -Force
$PptxManifestPath = Write-WebBundleManifest -BundlePath $PptxBundlePath
Test-WebBundleManifest -ManifestPath $PptxManifestPath -BundlePath $PptxBundlePath `
    -MismatchLabel "PPTX bundle hash mismatch"

$MdBundlePath = Join-Path $Root "assets\md-viewer"
$MdNoticePath = Join-Path $Root "web\md-viewer\THIRD_PARTY_NOTICES.txt"
if (-not (Test-Path (Join-Path $MdBundlePath "index.html"))) {
    throw "Markdown viewer build did not produce index.html"
}
Copy-Item $MdNoticePath (Join-Path $MdBundlePath "THIRD_PARTY_NOTICES.txt") -Force
$MdManifestPath = Write-WebBundleManifest -BundlePath $MdBundlePath
Test-WebBundleManifest -ManifestPath $MdManifestPath -BundlePath $MdBundlePath `
    -MismatchLabel "Markdown bundle hash mismatch"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create the Python virtual environment (exit $LASTEXITCODE)"
    }
}

$Python = Resolve-Path ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip (exit $LASTEXITCODE)"
}
& $Python -m pip install -e ".[dev]" pyinstaller
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install build dependencies (exit $LASTEXITCODE)"
}
& $Python scripts\generate_icons.py
if ($LASTEXITCODE -ne 0) {
    throw "Failed to generate application icons (exit $LASTEXITCODE)"
}

$DistPath = Join-Path $Root "dist"
$WorkPath = Join-Path $Root "build"
foreach ($Path in @($WorkPath, $DistPath)) {
    if (Test-Path $Path) {
        Remove-Item -Recurse -Force $Path
    }
}

& $Python -m PyInstaller reader.spec --noconfirm --clean --distpath $DistPath --workpath $WorkPath
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed (exit $LASTEXITCODE)"
}

if (-not (Test-Path "dist\Reader\Reader.exe")) {
    throw "dist\Reader\Reader.exe was not produced"
}

$FrozenPptxBundlePath = Join-Path $DistPath "Reader\_internal\assets\pptx-viewer"
$FrozenMdBundlePath = Join-Path $DistPath "Reader\_internal\assets\md-viewer"
$FrozenRuntimePaths = @(
    "Reader\_internal\assets\pptx-viewer\index.html",
    "Reader\_internal\assets\pptx-viewer\manifest.sha256",
    "Reader\_internal\assets\pptx-viewer\THIRD_PARTY_NOTICES.txt",
    "Reader\_internal\assets\md-viewer\index.html",
    "Reader\_internal\assets\md-viewer\manifest.sha256",
    "Reader\_internal\assets\md-viewer\THIRD_PARTY_NOTICES.txt",
    "Reader\_internal\PySide6\QtWebChannel.pyd"
)
foreach ($relative in $FrozenRuntimePaths) {
    if (-not (Test-Path (Join-Path $DistPath $relative))) {
        throw "Frozen runtime resource is missing: $relative"
    }
}
$FrozenPptxManifestPath = Join-Path $FrozenPptxBundlePath "manifest.sha256"
Test-WebBundleManifest -ManifestPath $FrozenPptxManifestPath -BundlePath $FrozenPptxBundlePath `
    -MismatchLabel "Frozen PPTX bundle hash mismatch"
$FrozenMdManifestPath = Join-Path $FrozenMdBundlePath "manifest.sha256"
Test-WebBundleManifest -ManifestPath $FrozenMdManifestPath -BundlePath $FrozenMdBundlePath `
    -MismatchLabel "Frozen Markdown bundle hash mismatch"

Write-Host "Built dist\Reader\Reader.exe"
