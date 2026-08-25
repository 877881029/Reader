import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "pptx-viewer"


def test_locked_supply_chain_and_node_floor():
    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((WEB / "package-lock.json").read_text(encoding="utf-8"))
    assert package["engines"] == {"node": ">=18"}
    assert package["dependencies"] == {"pptx-viewer": "0.2.2"}
    assert package["devDependencies"] == {
        "@types/node": "22.13.14",
        "jsdom": "24.1.3",
        "typescript": "5.9.2",
        "vite": "5.4.19",
        "vitest": "2.1.9",
    }
    assert lock["packages"]["node_modules/pptx-viewer"]["version"] == "0.2.2"
    assert lock["packages"]["node_modules/pptx-viewer"]["dependencies"] == {"fflate": "^0.8.2"}


def test_two_complete_mit_notices_and_ignore():
    lock = json.loads((WEB / "package-lock.json").read_text(encoding="utf-8"))
    fflate_version = lock["packages"]["node_modules/fflate"]["version"]
    notice = (WEB / "THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8")
    assert notice.count("MIT License") == 2
    assert "Copyright (c) 2025" in notice
    assert "Arjun Barrett" in notice
    assert f"fflate {fflate_version}" in notice
    assert "astx-jp" not in notice
    assert "web/pptx-viewer/node_modules/" in (ROOT / ".gitignore").read_text()


def test_vite_uses_jsdom_and_relative_bundle():
    config = (WEB / "vite.config.ts").read_text(encoding="utf-8")
    assert 'environment: "jsdom"' in config
    assert 'base: "./"' in config


def test_web_scaffold_keeps_local_bootstrap_only():
    index_html = (WEB / "index.html").read_text(encoding="utf-8")
    main_ts = (WEB / "src" / "main.ts").read_text(encoding="utf-8")
    assert '<main id="app"></main>' in index_html
    assert '<script src="qrc:///qtwebchannel/qwebchannel.js"></script>' in index_html
    assert "from \"http://" not in main_ts
    assert "from \"https://" not in main_ts
    assert not re.search(r"import\s*\(\s*['\"]https?://", main_ts)
