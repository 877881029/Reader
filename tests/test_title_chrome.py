from __future__ import annotations

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
