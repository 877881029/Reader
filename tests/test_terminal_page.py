from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication

from reader.shell.terminal_page import EXIT_HINT, TerminalPage

TIMEOUT = 25000


def _js(qtbot, page: TerminalPage, script: str):
    box: list = []
    page.view().page().runJavaScript(script, 0, box.append)
    qtbot.waitUntil(lambda: bool(box), timeout=TIMEOUT)
    return box[0]


def _text(qtbot, page: TerminalPage) -> str:
    return _js(qtbot, page, "window.readerTerminalText ? window.readerTerminalText() : ''") or ""


def _type(qtbot, page: TerminalPage, data: str) -> None:
    escaped = data.replace("\\", "\\\\").replace("'", "\\'").replace("\r", "\\r")
    _js(qtbot, page, f"window.readerTerminal.terminal.input('{escaped}', true); true")


@pytest.fixture
def cmd_page(qtbot, tmp_path: Path):
    page = TerminalPage("cmd", tmp_path)
    qtbot.addWidget(page)
    page.resize(900, 500)
    page.show()
    qtbot.waitExposed(page)
    qtbot.waitUntil(page.is_ready, timeout=TIMEOUT)
    yield page
    page.shutdown()


def test_profile_title_and_isolated_offline_profile(qtbot, tmp_path: Path):
    page = TerminalPage("powershell", tmp_path)
    qtbot.addWidget(page)
    try:
        assert page.objectName() == "terminalPage"
        assert page.title() == "PowerShell"
        assert page.cwd() == tmp_path
        assert page.view().page().profile().isOffTheRecord() is True
        bundle = page.bundle_root()
        assert page.allows_url(QUrl.fromLocalFile(str(bundle / "index.html")))
        assert page.allows_url(QUrl("qrc:///qtwebchannel/qwebchannel.js"))
        assert not page.allows_url(QUrl("https://example.com/x.js"))
        assert not page.allows_url(QUrl.fromLocalFile(str(tmp_path / "evil.js")))
    finally:
        page.shutdown()


def test_typed_command_output_reaches_xterm_with_copilot_theme(qtbot, cmd_page, tmp_path: Path):
    _type(qtbot, cmd_page, "echo READER_E2E 中文\r")
    qtbot.waitUntil(lambda: _text(qtbot, cmd_page).count("READER_E2E 中文") >= 2, timeout=TIMEOUT)
    assert str(tmp_path) in _text(qtbot, cmd_page)
    background = _js(qtbot, cmd_page, "getComputedStyle(document.body).backgroundColor")
    assert background == "rgb(246, 242, 238)"


def test_copy_text_goes_to_clipboard(qtbot, cmd_page, monkeypatch):
    copied: list[str] = []

    class FakeClipboard:
        def setText(self, text: str) -> None:  # noqa: N802 - Qt API
            copied.append(text)

    monkeypatch.setattr(QApplication, "clipboard", staticmethod(lambda: FakeClipboard()))
    cmd_page.bridge().copyText("from terminal")
    assert copied == ["from terminal"]


def test_exit_shows_hint_and_enter_restarts(qtbot, cmd_page):
    first = cmd_page.session()
    _type(qtbot, cmd_page, "exit\r")
    qtbot.waitUntil(lambda: EXIT_HINT in _text(qtbot, cmd_page), timeout=TIMEOUT)
    assert cmd_page.is_ready() is False

    _type(qtbot, cmd_page, "\r")
    qtbot.waitUntil(cmd_page.is_ready, timeout=TIMEOUT)
    assert cmd_page.session() is not first
    _type(qtbot, cmd_page, "echo AGAIN_OK\r")
    qtbot.waitUntil(lambda: _text(qtbot, cmd_page).count("AGAIN_OK") >= 2, timeout=TIMEOUT)


def test_shutdown_stops_shell(qtbot, cmd_page):
    session = cmd_page.session()
    assert session is not None and session.is_running()
    cmd_page.shutdown()
    cmd_page.shutdown()
    assert session.is_running() is False
