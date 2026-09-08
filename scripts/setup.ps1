[CmdletBinding()]
param(
    [switch]$SkipLaunch,
    [switch]$Dev
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

function Resolve-Python312 {
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        $executable = & py -3.12 -c "import sys; print(sys.executable)"
        if ($LASTEXITCODE -eq 0 -and $executable) {
            return ([string]$executable).Trim()
        }
    }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        & $python.Source -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)"
        if ($LASTEXITCODE -eq 0) {
            return $python.Source
        }
    }
    throw "Python 3.12+ is required. Install with: winget install Python.Python.3.12"
}

$python = Resolve-Python312
$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    & $python -m venv (Join-Path $Root ".venv")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create .venv (exit $LASTEXITCODE)"
    }
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip (exit $LASTEXITCODE)"
}

if ($Dev) {
    & $venvPython -m pip install -e ".[dev]"
} else {
    & $venvPython -m pip install -e .
}
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install Reader (exit $LASTEXITCODE)"
}

if (-not $SkipLaunch) {
    & $venvPython -m reader
    if ($LASTEXITCODE -ne 0) {
        throw "Reader failed to start (exit $LASTEXITCODE)"
    }
}
