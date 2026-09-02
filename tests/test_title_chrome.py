from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTabWidget, QWidget


def test_title_chrome_orders_icon_tabs_plus_caption(qtbot):
    from reader.shell.title_chrome import TitleChrome

    chrome = TitleChrome()
    qtbot.addWidget(chrome)
    tabs = QTabWidget()
    tabs.addTab(QWidget(), "a.md")
    chrome.adopt_tab_bar(tabs.tabBar())
    chrome.show()
    qtbot.waitExposed(chrome)

    icon = chrome.findChild(QWidget, "titleAppIcon")
    host = chrome.findChild(QWidget, "titleTabHost")
    plus = chrome.findChild(QWidget, "tabNewButton")
    caption = chrome.findChild(QWidget, "titleCaption")
    assert icon is not None and host is not None and plus is not None and caption is not None
    assert icon.x() < host.x() < plus.x() < caption.x()


def test_title_chrome_window_buttons_exist(qtbot):
    from reader.shell.title_chrome import TitleChrome

    chrome = TitleChrome()
    qtbot.addWidget(chrome)
    for name in ("titleMinButton", "titleMaxButton", "titleCloseButton"):
        assert chrome.findChild(QWidget, name) is not None


def test_caption_and_icon_press_start_system_move(qtbot, monkeypatch):
    from reader.shell.title_chrome import TitleChrome

    chrome = TitleChrome()
    qtbot.addWidget(chrome)
    chrome.show()
    qtbot.waitExposed(chrome)
    handle = chrome.windowHandle()
    assert handle is not None
    calls: list[str] = []
    monkeypatch.setattr(handle, "startSystemMove", lambda: calls.append("move") or True)

    caption = chrome.findChild(QWidget, "titleCaption")
    icon = chrome.findChild(QWidget, "titleAppIcon")
    plus = chrome.findChild(QWidget, "tabNewButton")
    assert caption is not None and icon is not None and plus is not None

    qtbot.mousePress(caption, Qt.MouseButton.LeftButton)
    qtbot.mousePress(icon, Qt.MouseButton.LeftButton)
    assert calls == ["move", "move"]

    qtbot.mousePress(plus, Qt.MouseButton.LeftButton)
    assert calls == ["move", "move"]


def test_title_chrome_matches_editor_white_without_bottom_border(qtbot):
    from reader.shell.title_chrome import TitleChrome

    chrome = TitleChrome()
    qtbot.addWidget(chrome)
    chrome.show()
    qtbot.waitExposed(chrome)
    sheet = chrome.styleSheet().replace(" ", "").lower()
    assert "background:#ffffff" in sheet
    assert "border-bottom:1px" not in sheet
