$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

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

Write-Host "Built dist\Reader\Reader.exe"
