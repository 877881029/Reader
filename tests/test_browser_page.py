from __future__ import annotations

import pytest

from reader.shell.browser_page import normalize_address


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://example.com/a?b=1", "https://example.com/a?b=1"),
        ("http://example.com", "http://example.com"),
        ("  example.com  ", "https://example.com"),
        ("docs.github.com/en", "https://docs.github.com/en"),
        ("localhost:8080", "http://localhost:8080"),
        ("localhost", "http://localhost"),
        ("file:///C:/tmp/a.html", "file:///C:/tmp/a.html"),
        ("hello world", "https://www.bing.com/search?q=hello%20world"),
        ("javascript:alert(1)", "https://www.bing.com/search?q=javascript%3Aalert(1)"),
        ("data:text/html,x", "https://www.bing.com/search?q=data%3Atext%2Fhtml%2Cx"),
        ("python", "https://www.bing.com/search?q=python"),
    ],
)
def test_normalize_address(text: str, expected: str) -> None:
    url = normalize_address(text)
    assert url is not None
    assert url.toString(url.ComponentFormattingOption.FullyEncoded) == expected


@pytest.mark.parametrize("text", ["", "   "])
def test_normalize_address_empty(text: str) -> None:
    assert normalize_address(text) is None


def _html(tmp_path, title: str = "Hi there"):
    page = tmp_path / "page.html"
    page.write_text(f"<html><head><title>{title}</title></head><body>body text</body></html>", encoding="utf-8")
    return page


def test_browser_page_isolated_profile_and_controls(qtbot):
    from PySide6.QtWebEngineCore import QWebEngineProfile
    from PySide6.QtWidgets import QLineEdit, QToolButton

    from reader.shell.browser_page import BrowserPage

    page = BrowserPage()
    qtbot.addWidget(page)
    try:
        assert page.objectName() == "browserPage"
        assert page.profile().isOffTheRecord() is True
        assert page.profile() is not QWebEngineProfile.defaultProfile()
        for name in ("browserBack", "browserForward", "browserReload"):
            assert page.findChild(QToolButton, name) is not None
        address = page.findChild(QLineEdit, "browserAddress")
        assert address is not None and address.placeholderText() == "输入网址或搜索"
    finally:
        page.shutdown()


def test_browser_page_address_enter_loads_local_file_and_reports_title(qtbot, tmp_path):
    from PySide6.QtWidgets import QLineEdit

    from reader.shell.browser_page import BrowserPage

    html = _html(tmp_path)
    page = BrowserPage()
    qtbot.addWidget(page)
    titles: list[str] = []
    page.title_changed.connect(titles.append)
    try:
        address = page.findChild(QLineEdit, "browserAddress")
        address.setText(html.as_uri())
        address.returnPressed.emit()
        # A fresh off-the-record profile starts its own Chromium renderer: 6–8 s
        # on a busy machine with endpoint scanning, so leave real headroom.
        qtbot.waitUntil(lambda: "Hi there" in titles, timeout=30000)
        qtbot.waitUntil(lambda: address.text() == html.as_uri(), timeout=5000)
    finally:
        page.shutdown()
    page.shutdown()
