import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_reader_spec_references_onedir_icon_version_and_webengine() -> None:
    spec = (ROOT / "reader.spec").read_text(encoding="utf-8")

    assert "name='Reader'" in spec
    assert "console=False" in spec
    assert "assets/icons/reader.ico" in spec.replace("\\", "/")
    assert "version_info.txt" in spec
    assert "collect_data_files('PySide6'" in spec
    assert "QtWebEngine" in spec
    assert "COLLECT(" in spec
    assert "(str(ROOT / 'assets/icons/reader.ico'), 'assets/icons')" in spec
    assert "(str(ROOT / 'assets/icons/reader-r.svg'), 'assets/icons')" in spec


def test_reader_spec_collects_complete_pptx_runtime_and_webchannel() -> None:
    spec = (ROOT / "reader.spec").read_text(encoding="utf-8")
    normalized = spec.replace("\\", "/")

    assert "collect_submodules('PySide6.QtWebChannel')" in spec
    assert (
        "(str(ROOT / 'assets/pptx-viewer'), 'assets/pptx-viewer')" in normalized
    )


def test_build_windows_script_is_clean_and_runs_the_spec() -> None:
    script = (ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")

    assert '& $Python -m pip install --upgrade pip' in script
    assert '& $Python -m pip install -e ".[dev]" pyinstaller' in script
    assert '& $Python scripts\\generate_icons.py' in script
    assert "Remove-Item -Recurse -Force" in script
    assert (
        "& $Python -m PyInstaller reader.spec --noconfirm --clean "
        "--distpath $DistPath --workpath $WorkPath"
    ) in script
    assert script.count("$LASTEXITCODE -ne 0") >= 5
    assert "dist\\Reader\\Reader.exe" in script


def test_build_script_runs_native_npm_checks_before_pyinstaller() -> None:
    script = (ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")

    required = [
        "Get-Command node.exe",
        "Get-Command npm.cmd",
        "$npmDir = Split-Path -Parent $npm.Source",
        '$npmRelativeNode = Join-Path $npmDir "node.exe"',
        "Test-Path $npmRelativeNode -PathType Leaf",
        "$nodePath = (Resolve-Path $npmRelativeNode).Path",
        "$nodePath = (Get-Command node.exe -ErrorAction Stop).Source",
        "& $nodePath --version",
        "Node.js 18+ is required at $nodePath",
        "Start-Process",
        '"/d", "/s", "/c"',
        "$process.ExitCode",
        'Invoke-Npm "ci --prefix web\\pptx-viewer"',
        'Invoke-Npm "run build --prefix web\\pptx-viewer"',
    ]
    for fragment in required:
        assert fragment in script
    assert "$major -lt 18" in script

    npm_lookup = script.index("Get-Command npm.cmd")
    npm_relative = script.index("$npmRelativeNode")
    fallback = script.index("Get-Command node.exe")
    npm_ci = script.index('Invoke-Npm "ci --prefix web\\pptx-viewer"')
    npm_build = script.index('Invoke-Npm "run build --prefix web\\pptx-viewer"')
    manifest = script.index("manifest.sha256")
    pyinstaller = script.index("-m PyInstaller")
    assert npm_lookup < npm_relative < fallback < npm_ci
    assert npm_ci < npm_build < manifest < pyinstaller


def test_manifest_paths_support_windows_powershell() -> None:
    script = (ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")

    assert "[IO.Path]::GetRelativePath" not in script
    assert ".Substring($bundleRoot.Length + 1)" in script


def test_build_verifies_frozen_pptx_runtime_and_webchannel() -> None:
    script = (ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")

    assert "_internal\\assets\\pptx-viewer\\index.html" in script
    assert "_internal\\assets\\pptx-viewer\\manifest.sha256" in script
    assert "_internal\\assets\\pptx-viewer\\THIRD_PARTY_NOTICES.txt" in script
    assert "_internal\\PySide6\\QtWebChannel.pyd" in script
    assert "Frozen runtime resource is missing" in script
    assert "function Test-PptxManifest" in script
    assert script.count("Test-PptxManifest -ManifestPath") == 2
    assert "[string]::IsNullOrWhiteSpace($line)" in script
    assert '$line -notmatch "^[0-9a-f]{64}  .+$"' in script


def test_npm_failure_stops_before_cleanup_and_pyinstaller(tmp_path) -> None:
    powershell = shutil.which("powershell.exe")
    node = shutil.which("node.exe")
    if powershell is None or node is None:
        pytest.skip("PowerShell and Node.js are required for native build failure test")

    root = tmp_path / "isolated-build"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(ROOT / "scripts" / "build_windows.ps1", scripts / "build_windows.ps1")
    sentinel = root / "dist" / "must-survive.txt"
    sentinel.parent.mkdir()
    sentinel.write_text("not touched", encoding="utf-8")

    fake_bin = tmp_path / "fake bin"
    fake_bin.mkdir()
    npm_relative_node = fake_bin / "node.exe"
    shutil.copy2(node, npm_relative_node)
    npm_log = tmp_path / "npm.log"
    (fake_bin / "npm.cmd").write_text(
        '@echo off\r\necho %*>>"%READER_FAKE_NPM_LOG%"\r\nexit /b 23\r\n',
        encoding="ascii",
    )
    path_first = tmp_path / "path-first-node"
    path_first.mkdir()
    shutil.copy2(node, path_first / "node.exe")
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join((str(path_first), str(fake_bin), env["PATH"]))
    env["READER_FAKE_NPM_LOG"] = str(npm_log)

    result = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(scripts / "build_windows.ps1"),
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert f"Using Node.js from {npm_relative_node}" in output
    assert f"Using Node.js from {path_first / 'node.exe'}" not in output
    assert npm_log.read_text(encoding="utf-8").strip() == "ci --prefix web\\pptx-viewer"
    assert "npm ci --prefix web\\pptx-viewer failed (exit 23)" in output
    assert sentinel.read_text(encoding="utf-8") == "not touched"


def test_reader_spec_is_not_ignored_by_git() -> None:
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "reader.spec"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1, result.stdout + result.stderr


def test_pyinstaller_is_a_packaging_development_dependency() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"pyinstaller>=' in pyproject.lower()


def test_runtime_icon_paths_use_shared_frozen_aware_resource_helper(monkeypatch) -> None:
    resources = (ROOT / "src" / "reader" / "resources.py").read_text(encoding="utf-8")
    app = (ROOT / "src" / "reader" / "app.py").read_text(encoding="utf-8")
    window = (ROOT / "src" / "reader" / "shell" / "window.py").read_text(
        encoding="utf-8"
    )

    assert "sys._MEIPASS" in resources
    assert "def resource_path(" in resources
    assert 'resource_path("assets", "icons", "reader.ico")' in app
    assert 'resource_path("assets", "icons", "reader.ico")' in window

    monkeypatch.delattr(sys, "frozen", raising=False)
    from reader.resources import resource_path

    icon = resource_path("assets", "icons", "reader.ico")
    assert icon == ROOT / "assets" / "icons" / "reader.ico"
    assert icon.is_file()


def test_packaging_smoke_can_disable_real_shell_integration() -> None:
    main = (ROOT / "src" / "reader" / "__main__.py").read_text(encoding="utf-8")

    assert "if not _shell_integration_disabled():" in main
    assert "register_open_with(exe, args=args)" in main
    assert "create_desktop_shortcut(exe, args=args, icon=exe)" in main


def test_windows_gui_smoke_script_declares_strict_telemetry_and_cleanup() -> None:
    script = (ROOT / "scripts" / "smoke_windows.ps1").read_text(encoding="utf-8")

    assert "READER_SKIP_SHELL_INTEGRATION" in script
    assert "READER_IPC_NAMESPACE" in script
    assert "READER_SMOKE_BATCH_LOG" in script
    assert "QTWEBENGINE_CHROMIUM_FLAGS" in script
    assert '"TEMP"' in script
    assert '"TMP"' in script
    assert script.count("Start-Process") >= 2
    assert "$baselineReaderProcessIds" in script
    assert "$secondaries" in script
    assert "MainWindowHandle" in script
    assert "Get-CimInstance Win32_Process" in script
    assert "ConvertFrom-Json" in script
    assert "reader-single-instance-locks" in script
    assert "WaitForExit" in script
    assert "Stop-Process" in script
    assert "Stop-Process -Id $processId -Force" in script
    assert "Failed to remove smoke test root" in script
    assert not re.search(
        r"Remove-Item[^\r\n]*-ErrorAction\s+SilentlyContinue",
        script,
    )
    assert "$smokeError" in script
    assert "} catch {" in script
    assert "Resolve-SmokeFailure" in script
    finally_body = script.split("} finally {", 1)[1].split(
        "$resolvedFailure",
        1,
    )[0]
    assert "throw " not in finally_body
    assert "Reader GUI smoke passed" in script


@pytest.mark.skipif(
    shutil.which("powershell.exe") is None,
    reason="PowerShell is required for smoke helper execution",
)
def test_smoke_failure_resolver_preserves_business_error_before_cleanup() -> None:
    helper = ROOT / "scripts" / "smoke_helpers.ps1"
    command = f"""
. '{helper}'
$none = Resolve-SmokeFailure -SmokeError $null -CleanupFailures @()
if ($null -ne $none) {{ throw "no-error quadrant returned a failure" }}
try {{ throw "business-original" }} catch {{ $business = $_ }}
$businessOnly = Resolve-SmokeFailure -SmokeError $business -CleanupFailures @()
if ($businessOnly.Exception.Message -ne "business-original") {{
    throw "business-only quadrant lost the original error"
}}
$cleanupOnly = Resolve-SmokeFailure -SmokeError $null -CleanupFailures @("cleanup-only")
if ($cleanupOnly.Exception.Message -notmatch "cleanup-only") {{
    throw "cleanup-only quadrant lost cleanup diagnostics"
}}
$both = Resolve-SmokeFailure -SmokeError $business -CleanupFailures @("cleanup-appended")
$message = $both.Exception.Message
if ($message.IndexOf("business-original") -lt 0) {{
    throw "combined quadrant lost business error"
}}
if ($message.IndexOf("cleanup-appended") -lt 0) {{
    throw "combined quadrant lost cleanup error"
}}
if ($message.IndexOf("business-original") -gt $message.IndexOf("cleanup-appended")) {{
    throw "combined quadrant did not keep business error first"
}}
throw $both
"""
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "business-original" in output
    assert "cleanup-appended" in output
    assert output.index("business-original") < output.index("cleanup-appended")
