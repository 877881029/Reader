import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "md-viewer"
EXPECTED_DEV_DEPENDENCIES = {
    "@types/markdown-it": "14.2.0",
    "@types/node": "22.13.14",
    "jsdom": "24.1.3",
    "typescript": "5.9.2",
    "vite": "5.4.19",
    "vitest": "2.1.9",
}


def _is_node18_compatible(node_engine: str) -> bool:
    compact = node_engine.replace(" ", "")
    if "18" in compact:
        return True
    if compact.startswith(">="):
        digits = []
        for ch in compact[2:]:
            if ch.isdigit():
                digits.append(ch)
            else:
                break
        return bool(digits) and int("".join(digits)) <= 18
    if compact.startswith(("^", "~")):
        digits = []
        for ch in compact[1:]:
            if ch.isdigit():
                digits.append(ch)
            else:
                break
        return bool(digits) and int("".join(digits)) <= 18
    return False


def test_md_viewer_supply_chain_is_exact_and_offline():
    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((WEB / "package-lock.json").read_text(encoding="utf-8"))
    assert package["engines"] == {"node": ">=18"}
    assert lock["name"] == "reader-md-viewer"
    assert lock["version"] == "0.1.0"
    assert lock["packages"][""]["name"] == "reader-md-viewer"
    assert lock["packages"][""]["version"] == "0.1.0"
    assert set(package["dependencies"]) == {"markdown-it", "mermaid"}
    assert all(not value.startswith(("^", "~")) for value in package["dependencies"].values())
    assert package["devDependencies"] == EXPECTED_DEV_DEPENDENCIES
    assert all(not value.startswith(("^", "~")) for value in package["devDependencies"].values())
    for dep_name in sorted(package["devDependencies"]):
        dep_package = json.loads((WEB / "node_modules" / dep_name / "package.json").read_text(encoding="utf-8"))
        node_engine = dep_package.get("engines", {}).get("node")
        if node_engine is not None:
            assert _is_node18_compatible(node_engine), f"{dep_name} requires unsupported node range: {node_engine}"

    index_html = (WEB / "index.html").read_text(encoding="utf-8")
    assert "<main id=\"app\"></main>" in index_html
    assert "qrc:///qtwebchannel/qwebchannel.js" in index_html
    assert "http://" not in index_html and "https://" not in index_html


def test_notices_cover_every_production_dependency_tree_entry():
    result = subprocess.run(
        ["npm.cmd", "ls", "--omit=dev", "--all", "--json"],
        cwd=WEB,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    tree = json.loads(result.stdout)
    notice = (WEB / "THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8")

    expected = set()

    def walk(node: dict) -> None:
        deps = node.get("dependencies", {})
        for name, child in deps.items():
            version = child.get("version")
            if version:
                expected.add(f"{name} {version}")
            walk(child)

    walk(tree)
    assert expected
    for item in sorted(expected):
        assert item in notice

    source_notice = (WEB / "THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8")
    bundled_notice = (ROOT / "assets" / "md-viewer" / "THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8")
    assert source_notice == bundled_notice
    for content in (source_notice, bundled_notice):
        assert str(ROOT) not in content
        assert ROOT.as_posix() not in content
        for line in content.splitlines():
            if not line.startswith("License file: "):
                continue
            path_value = line.removeprefix("License file: ")
            assert "\\" not in path_value
            assert not re.search(r"^[A-Za-z]:/", path_value)
            assert path_value.startswith("node_modules/")


def test_committed_md_bundle_manifest_matches_bytes():
    bundle = ROOT / "assets" / "md-viewer"
    manifest = bundle / "manifest.sha256"
    assert (bundle / "index.html").is_file()
    assert (bundle / "THIRD_PARTY_NOTICES.txt").is_file()
    assert manifest.is_file()

    expected = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(bundle).as_posix()}"
        for path in sorted(
            (p for p in bundle.rglob("*") if p.is_file() and p != manifest),
            key=lambda p: p.relative_to(bundle).as_posix(),
        )
    ]
    assert manifest.read_text(encoding="ascii").splitlines() == expected


def test_notices_script_uses_internal_tree_walker():
    script = (WEB / "scripts" / "generate-notices.mjs").read_text(encoding="utf-8")
    assert "license-checker-rseidelsohn" not in script
    assert "npm ls --omit=dev --all --json" in script
    assert "Missing license text" in script


def test_notice_path_label_is_stable_across_roots():
    result = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            (
                "import { toPackageRelativeLabel } from './scripts/generate-notices.mjs'; "
                "const a = toPackageRelativeLabel('C:/repo/web/md-viewer', 'C:/repo/web/md-viewer/node_modules/pkg', 'LICENSE'); "
                "const b = toPackageRelativeLabel('D:/other/web/md-viewer', 'D:/other/web/md-viewer/node_modules/pkg', 'LICENSE'); "
                "console.log(JSON.stringify({ a, b }));"
            ),
        ],
        cwd=WEB,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    labels = json.loads(result.stdout)
    assert labels == {"a": "node_modules/pkg/LICENSE", "b": "node_modules/pkg/LICENSE"}


def test_manifest_script_is_wired_into_build():
    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    assert package["scripts"]["manifest"] == "node scripts/generate-manifest.mjs"
    assert package["scripts"]["build"] == "npm run typecheck && vite build && npm run notices && npm run manifest"

    script = (WEB / "scripts" / "generate-manifest.mjs").read_text(encoding="utf-8")
    assert "manifest.sha256" in script
    assert "createHash(\"sha256\")" in script


def test_clean_build_restores_notices_and_manifest(tmp_path):
    if os.environ.get("READER_RUN_NPM_BUILD_TEST") != "1":
        return

    bundle = ROOT / "assets" / "md-viewer"
    backup = tmp_path / "md-viewer-backup"
    if bundle.exists():
        shutil.copytree(bundle, backup)
    shutil.rmtree(bundle, ignore_errors=True)

    try:
        result = subprocess.run(
            ["npm.cmd", "run", "build"],
            cwd=WEB,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert (bundle / "index.html").is_file()
        assert (bundle / "THIRD_PARTY_NOTICES.txt").is_file()
        assert (bundle / "manifest.sha256").is_file()
        test_committed_md_bundle_manifest_matches_bytes()
    finally:
        if backup.exists():
            shutil.rmtree(bundle, ignore_errors=True)
            shutil.copytree(backup, bundle)
