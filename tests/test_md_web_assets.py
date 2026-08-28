import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "md-viewer"


def test_md_viewer_supply_chain_is_exact_and_offline():
    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    assert package["engines"] == {"node": ">=18"}
    assert set(package["dependencies"]) == {"markdown-it", "mermaid"}
    assert all(not value.startswith(("^", "~")) for value in package["dependencies"].values())
    assert all(not value.startswith(("^", "~")) for value in package["devDependencies"].values())

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
