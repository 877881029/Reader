from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STALE_SPEC_STATUS = re.compile(
    r"Draft for user review|awaiting implementation plan|\bimplementing\b",
    re.IGNORECASE,
)


def test_generated_logs_are_ignored() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert "/logs/" in ignore
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "logs/bvm/bvm.log"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_package_description_matches_current_product_scope() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert (
        'description = "Windows multi-format document viewer"' in pyproject
    )


def test_specification_headers_do_not_claim_completed_work_is_pending() -> None:
    stale: list[str] = []
    specs = ROOT / "docs" / "superpowers" / "specs"

    for path in sorted(specs.glob("*.md")):
        header = "\n".join(path.read_text(encoding="utf-8").splitlines()[:6])
        match = STALE_SPEC_STATUS.search(header)
        if match:
            stale.append(f"{path.name}: {match.group(0)}")

    assert stale == []


def test_windows_quality_workflow_runs_unified_gate_with_pinned_toolchains() -> None:
    workflow = (
        ROOT / ".github" / "workflows" / "quality.yml"
    ).read_text(encoding="utf-8")

    required = [
        "permissions:\n  contents: read",
        "concurrency:",
        "cancel-in-progress: true",
        "runs-on: windows-latest",
        "actions/checkout@v5",
        "actions/setup-python@v6",
        "python-version: '3.12'",
        "cache: pip",
        "cache-dependency-path: pyproject.toml",
        "actions/setup-node@v5",
        "node-version: '22'",
        "cache: npm",
        "web/pptx-viewer/package-lock.json",
        "web/md-viewer/package-lock.json",
        'python -m pip install -e ".[dev]"',
        "scripts\\verify.ps1 -Python python",
    ]
    for fragment in required:
        assert fragment in workflow
    assert "office" not in workflow.lower()


def test_webengine_test_process_disables_chromium_sandbox():
    import os

    assert os.environ.get("QTWEBENGINE_DISABLE_SANDBOX") == "1"


def test_web_bundle_notices_and_manifests_stay_tracked():
    # The build briefly deletes these; an interrupted build must not be committed.
    tracked = subprocess.run(
        ["git", "ls-files", "assets/pptx-viewer", "assets/md-viewer", "assets/terminal-viewer"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    for bundle in ("pptx-viewer", "md-viewer", "terminal-viewer"):
        for name in ("THIRD_PARTY_NOTICES.txt", "manifest.sha256", "index.html"):
            assert f"assets/{bundle}/{name}" in tracked



def test_dependencies_are_pinned_to_the_tested_versions():
    import re
    import tomllib
    from importlib.metadata import version

    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    requirements = project["dependencies"] + project["optional-dependencies"]["dev"]
    for requirement in requirements:
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([0-9][0-9A-Za-z.]*)", requirement)
        assert match, f"not pinned: {requirement}"
        name, pinned = match.groups()
        assert version(name) == pinned, f"{name}: pinned {pinned}, installed {version(name)}"



def test_dead_code_and_stray_reports_are_removed():
    root = Path(__file__).resolve().parents[1]
    for relative in (
        "src/reader/shell/settings_claim.py",
        "src/reader/ext",
        "task-2-report.md",
        "task-3-report.md",
        "task-5-report.md",
        "task-6-report.md",
    ):
        assert not (root / relative).exists(), relative
    for source in (root / "src").rglob("*.py"):
        text = source.read_text(encoding="utf-8")
        assert "settings_claim" not in text, source
        assert "reader.ext" not in text, source



def test_status_is_a_short_handoff_page():
    root = Path(__file__).resolve().parents[1]
    status = (root / "docs" / "STATUS.md").read_text(encoding="utf-8")
    headings = [line for line in status.splitlines() if line.startswith("## ")]
    assert headings[:4] == ["## 当前状态", "## 每次更新必做", "## 当前目标", "## 历史要点"]
    assert len(status.splitlines()) < 250
