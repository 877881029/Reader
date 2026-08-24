import re
import subprocess
import sys
from pathlib import Path


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
    assert "Reader GUI smoke passed" in script
