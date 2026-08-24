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


def test_build_windows_script_is_clean_and_runs_the_spec() -> None:
    script = (ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")

    assert 'pip install -e ".[dev]" pyinstaller' in script
    assert "Remove-Item -Recurse -Force" in script
    assert "pyinstaller reader.spec --noconfirm --clean" in script
    assert "dist\\Reader\\Reader.exe" in script


def test_pyinstaller_is_a_packaging_development_dependency() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"pyinstaller>=' in pyproject.lower()


def test_runtime_icon_paths_use_shared_frozen_aware_resource_helper() -> None:
    resources = (ROOT / "src" / "reader" / "resources.py").read_text(encoding="utf-8")
    app = (ROOT / "src" / "reader" / "app.py").read_text(encoding="utf-8")
    window = (ROOT / "src" / "reader" / "shell" / "window.py").read_text(
        encoding="utf-8"
    )

    assert "sys._MEIPASS" in resources
    assert "def resource_path(" in resources
    assert 'resource_path("assets", "icons", "reader.ico")' in app
    assert 'resource_path("assets", "icons", "reader.ico")' in window


def test_packaging_smoke_can_disable_real_shell_integration() -> None:
    main = (ROOT / "src" / "reader" / "__main__.py").read_text(encoding="utf-8")

    assert 'os.environ.get("READER_SKIP_SHELL_INTEGRATION")' in main
