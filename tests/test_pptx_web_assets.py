import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "pptx-viewer"


def test_locked_supply_chain_and_node_floor():
    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((WEB / "package-lock.json").read_text(encoding="utf-8"))
    assert package["engines"] == {"node": ">=18"}
    assert package["dependencies"] == {"pptx-viewer": "0.2.2"}
    assert package["devDependencies"]["@types/node"].startswith("^")
    assert lock["packages"]["node_modules/pptx-viewer"]["version"] == "0.2.2"
    assert lock["packages"]["node_modules/pptx-viewer"]["dependencies"] == {"fflate": "^0.8.2"}


def test_two_complete_mit_notices_and_ignore():
    notice = (WEB / "THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8")
    assert notice.count("MIT License") == 2
    assert "Copyright (c) 2025" in notice
    assert "Copyright (c) 2023 Arjun Barrett" in notice
    assert "astx-jp" not in notice
    assert "web/pptx-viewer/node_modules/" in (ROOT / ".gitignore").read_text()


def test_vite_uses_jsdom_and_relative_bundle():
    config = (WEB / "vite.config.ts").read_text(encoding="utf-8")
    assert 'environment: "jsdom"' in config
    assert 'base: "./"' in config
