[CmdletBinding()]
param(
    [string]$Source = "",
    [string]$Destination = "",
    [string]$Python = ""
)

# Installs a built Reader (dist\Reader) to a stable per-user location and points
# the desktop shortcut and file associations at it.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $Source) { $Source = Join-Path $Root "dist\Reader" }
if (-not $Destination) { $Destination = Join-Path $env:LOCALAPPDATA "Programs\Reader" }
if (-not $Python) {
    $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
    $Python = if (Test-Path $venvPython) { $venvPython } else { "python" }
}

$sourceExe = Join-Path $Source "Reader.exe"
if (-not (Test-Path $sourceExe)) {
    throw "Build not found: $sourceExe (run scripts\build_windows.ps1 first)"
}

$destinationFull = [System.IO.Path]::GetFullPath($Destination)
$running = Get-Process -Name Reader -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -and $_.Path.StartsWith($destinationFull, [System.StringComparison]::OrdinalIgnoreCase)
}
if ($running) {
    throw "Reader is running from $destinationFull (PID $($running.Id -join ', ')); close it first."
}

New-Item -ItemType Directory -Force -Path $destinationFull | Out-Null
& robocopy $Source $destinationFull /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) {
    throw "robocopy failed (exit $LASTEXITCODE)"
}

$installedExe = Join-Path $destinationFull "Reader.exe"
$sourceHash = (Get-FileHash $sourceExe -Algorithm SHA256).Hash
$installedHash = (Get-FileHash $installedExe -Algorithm SHA256).Hash
if ($sourceHash -ne $installedHash) {
    throw "Installed Reader.exe hash mismatch ($installedHash != $sourceHash)"
}

$icon = Join-Path $destinationFull "_internal\assets\icons\reader.ico"
$register = @"
from reader.shell.associate import create_desktop_shortcut, register_open_with
exe = r'$installedExe'
register_open_with(exe, args=())
print(create_desktop_shortcut(exe, args=(), icon=r'$icon', overwrite=True))
"@
$previousPath = $env:PYTHONPATH
$env:PYTHONPATH = Join-Path $Root "src"
try {
    $register | & $Python -
    if ($LASTEXITCODE -ne 0) {
        throw "Shell registration failed (exit $LASTEXITCODE)"
    }
} finally {
    $env:PYTHONPATH = $previousPath
}

Write-Host "Reader installed: $installedExe"
Write-Host "SHA256: $installedHash"
