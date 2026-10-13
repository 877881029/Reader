from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "terminal-viewer"
BUNDLE = ROOT / "assets" / "terminal-viewer"


def test_package_pins_xterm_versions():
    package = (WEB / "package.json").read_text(encoding="utf-8")
    assert '"@xterm/xterm": "6.0.0"' in package
    assert '"@xterm/addon-fit": "0.11.0"' in package
    assert (WEB / "package-lock.json").is_file()


def test_bundle_manifest_matches_files():
    lines = (BUNDLE / "manifest.sha256").read_text(encoding="ascii").splitlines()
    listed = {}
    for line in lines:
        digest, relative = line.split("  ", 1)
        listed[relative] = digest
    files = {
        path.relative_to(BUNDLE).as_posix()
        for path in BUNDLE.rglob("*")
        if path.is_file() and path.name != "manifest.sha256"
    }
    assert set(listed) == files
    for relative, digest in listed.items():
        assert hashlib.sha256((BUNDLE / relative).read_bytes()).hexdigest() == digest


def test_bundle_is_offline_and_uses_webchannel():
    html = (BUNDLE / "index.html").read_text(encoding="utf-8")
    assert "qrc:///qtwebchannel/qwebchannel.js" in html
    assert not re.search(r"https?://", html)
    script = next((BUNDLE / "assets").glob("index-*.js")).read_text(encoding="utf-8")
    assert "readerTerminalText" in script


def test_notices_cover_xterm_packages():
    notice = (BUNDLE / "THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8")
    assert "## @xterm/xterm 6.0.0" in notice
    assert "## @xterm/addon-fit 0.11.0" in notice
    assert notice == (WEB / "THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8")


def test_bundle_has_no_misminified_xterm_request_mode():
    script = next((BUNDLE / "assets").glob("index-*.js")).read_text(encoding="utf-8")
    assert "void 0||(i={})" not in script
    assert "requestMode(" in script
