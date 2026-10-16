from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _current() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def test_version_file_is_single_semver_line():
    text = (ROOT / "VERSION").read_text(encoding="utf-8")
    assert re.fullmatch(r"\d+\.\d+\.\d+\n?", text)


def test_pyproject_reads_version_from_version_file():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'dynamic = ["version"]' in pyproject
    assert 'version = { file = "VERSION" }' in pyproject
    project = pyproject.split("[project]", 1)[1].split("\n[", 1)[0]
    assert not re.search(r'^version\s*=', project, re.MULTILINE)


def test_windows_version_resource_is_generated_not_committed():
    tools = _load("version_tools")
    assert not (ROOT / "version_info.txt").exists()
    spec = (ROOT / "reader.spec").read_text(encoding="utf-8")
    assert "write_win32_version_info(" in spec
    info = tools.win32_version_info("1.2.3")
    assert "filevers=(1, 2, 3, 0)" in info
    assert "prodvers=(1, 2, 3, 0)" in info
    assert "StringStruct('FileVersion', '1.2.3')" in info
    assert "StringStruct('ProductVersion', '1.2.3')" in info


def test_docs_mention_current_version():
    version = _current()
    assert f"当前版本 **{version}**" in (ROOT / "README.md").read_text(encoding="utf-8")


def _fake_repo(tmp_path: Path, version: str = "0.1.0") -> Path:
    (tmp_path / "VERSION").write_text(version + "\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        f"# Reader\n\nWindows 桌面文档查看器，当前版本 **{version}**。\n\n不改：0.1.0 历史说明\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.mark.parametrize(
    ("args", "expected"),
    [([], "0.1.1"), (["--minor"], "0.2.0"), (["--major"], "1.0.0"), (["--set", "2.0.5"], "2.0.5")],
)
def test_bump_updates_version_and_readme(tmp_path, args, expected):
    bump = _load("bump_version")
    root = _fake_repo(tmp_path)

    assert bump.main(["--root", str(root), *args]) == 0

    assert (root / "VERSION").read_text(encoding="utf-8") == expected + "\n"
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert f"当前版本 **{expected}**" in readme
    assert "不改：0.1.0 历史说明" in readme


def test_bump_carries_over_large_patch_numbers(tmp_path):
    bump = _load("bump_version")
    root = _fake_repo(tmp_path, "1.0.25")

    assert bump.main(["--root", str(root)]) == 0
    assert (root / "VERSION").read_text(encoding="utf-8") == "1.0.26\n"


def test_bump_rejects_bad_version_and_changes_nothing(tmp_path):
    bump = _load("bump_version")
    root = _fake_repo(tmp_path)
    before = {p.name: p.read_bytes() for p in root.iterdir()}

    assert bump.main(["--root", str(root), "--set", "1.2"]) != 0
    assert {p.name: p.read_bytes() for p in root.iterdir()} == before


def test_bump_script_runs_from_command_line(tmp_path):
    root = _fake_repo(tmp_path)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "bump_version.py"), "--root", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    assert "0.1.0 -> 0.1.1" in result.stdout


def test_release_rule_is_in_handoff_docs():
    for doc in ("AGENTS.md", "docs/superpowers/process.md", ".cursor/rules/git-progress-handoff.mdc"):
        assert "bump_version.py" in (ROOT / doc).read_text(encoding="utf-8"), doc
