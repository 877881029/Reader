$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
}

$Python = Resolve-Path ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -e ".[dev]" pyinstaller
& $Python scripts\generate_icons.py

foreach ($Path in @("build", "dist")) {
    if (Test-Path $Path) {
        Remove-Item -Recurse -Force $Path
    }
}

$env:PATH = "$(Split-Path $Python);$env:PATH"
pyinstaller reader.spec --noconfirm --clean

if (-not (Test-Path "dist\Reader\Reader.exe")) {
    throw "dist\Reader\Reader.exe was not produced"
}

Write-Host "Built dist\Reader\Reader.exe"
