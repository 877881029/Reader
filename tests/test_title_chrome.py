from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
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
    icon_x = icon.mapTo(chrome, icon.rect().topLeft()).x()
    host_x = host.mapTo(chrome, host.rect().topLeft()).x()
    plus_x = plus.mapTo(chrome, plus.rect().topLeft()).x()
    caption_x = caption.mapTo(chrome, caption.rect().topLeft()).x()
    assert icon_x < host_x < plus_x < caption_x
    host_right = host.mapTo(chrome, QPoint(host.width(), 0)).x()
    plus_left = plus.mapTo(chrome, QPoint(0, 0)).x()
    assert plus_left - host_right <= 2


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

    qtbot.mousePress(caption, Qt.MouseButton.LeftButton)
    assert calls == ["move", "move", "move"]

    qtbot.mousePress(plus, Qt.MouseButton.LeftButton)
    assert calls == ["move", "move", "move"]


def test_title_chrome_is_notepad_gray(qtbot):
    from reader.shell.title_chrome import TitleChrome

    chrome = TitleChrome()
    qtbot.addWidget(chrome)
    chrome.show()
    qtbot.waitExposed(chrome)
    sheet = chrome.styleSheet().replace(" ", "").lower()
    assert "qwidget#titlechrome" in sheet
    assert "background:#f3f3f3" in sheet
    assert "qtabbar::tab:selected" in sheet
    assert "background:#f9f9f9" in sheet
    assert "border-bottom:1px" not in sheet
    assert "titleminbutton:hover" in sheet
    assert "background:#e5e5e5" in sheet
    assert "titleclosebutton:hover" in sheet
    assert "#e81123" in sheet
    min_btn = chrome.findChild(QWidget, "titleMinButton")
    close_btn = chrome.findChild(QWidget, "titleCloseButton")
    assert min_btn is not None and close_btn is not None
    button_sheet = min_btn.styleSheet().replace(" ", "").lower() + sheet
    assert "background:#f3f3f3" in button_sheet
