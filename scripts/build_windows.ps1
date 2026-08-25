$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$node = Get-Command node.exe -ErrorAction Stop
$npm = Get-Command npm.cmd -ErrorAction Stop
$major = [int]((& $node.Source --version).TrimStart("v").Split(".")[0])
if ($LASTEXITCODE -ne 0 -or $major -lt 18) {
    throw "Node.js 18+ is required"
}

function Invoke-Npm([string]$Arguments) {
    $process = Start-Process -FilePath $env:ComSpec `
        -ArgumentList @("/d", "/s", "/c", "call `"$($npm.Source)`" $Arguments") `
        -WorkingDirectory $Root -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -ne 0) {
        throw "npm $Arguments failed (exit $($process.ExitCode))"
    }
}

Invoke-Npm "ci --prefix web\pptx-viewer"
Invoke-Npm "run build --prefix web\pptx-viewer"

$BundlePath = Join-Path $Root "assets\pptx-viewer"
$NoticePath = Join-Path $Root "web\pptx-viewer\THIRD_PARTY_NOTICES.txt"
if (-not (Test-Path (Join-Path $BundlePath "index.html"))) {
    throw "PPTX viewer build did not produce index.html"
}
Copy-Item $NoticePath (Join-Path $BundlePath "THIRD_PARTY_NOTICES.txt") -Force

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
$ManifestPath = Join-Path $BundlePath "manifest.sha256"
$lines | Set-Content $ManifestPath -Encoding ascii
foreach ($line in Get-Content $ManifestPath) {
    $hash, $relative = $line -split "  ", 2
    if (-not $hash -or -not $relative) {
        throw "Invalid PPTX bundle manifest entry: $line"
    }
    $actual = (
        Get-FileHash (Join-Path $BundlePath $relative) -Algorithm SHA256
    ).Hash.ToLower()
    if ($actual -ne $hash) {
        throw "PPTX bundle hash mismatch: $relative"
    }
}

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

$FrozenBundlePath = Join-Path $DistPath "Reader\_internal\assets\pptx-viewer"
$FrozenRuntimePaths = @(
    "Reader\_internal\assets\pptx-viewer\index.html",
    "Reader\_internal\assets\pptx-viewer\manifest.sha256",
    "Reader\_internal\assets\pptx-viewer\THIRD_PARTY_NOTICES.txt",
    "Reader\_internal\PySide6\QtWebChannel.pyd"
)
foreach ($relative in $FrozenRuntimePaths) {
    if (-not (Test-Path (Join-Path $DistPath $relative))) {
        throw "Frozen runtime resource is missing: $relative"
    }
}
foreach ($line in Get-Content (Join-Path $FrozenBundlePath "manifest.sha256")) {
    $hash, $relative = $line -split "  ", 2
    $actual = (
        Get-FileHash (Join-Path $FrozenBundlePath $relative) -Algorithm SHA256
    ).Hash.ToLower()
    if ($actual -ne $hash) {
        throw "Frozen PPTX bundle hash mismatch: $relative"
    }
}

Write-Host "Built dist\Reader\Reader.exe"
