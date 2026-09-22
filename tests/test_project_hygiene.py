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
