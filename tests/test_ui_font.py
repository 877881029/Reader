from __future__ import annotations

import ctypes
from ctypes import wintypes

import pytest
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QAbstractButton, QApplication, QLabel, QTabBar, QWidget

_GGI_MARK_NONEXISTING_GLYPHS = 1
_MISSING = 0xFFFF


def _gdi():
    gdi = ctypes.WinDLL("gdi32")
    user = ctypes.WinDLL("user32")
    gdi.CreateFontW.restype = wintypes.HFONT
    gdi.CreateFontW.argtypes = [ctypes.c_int] * 5 + [wintypes.DWORD] * 8 + [wintypes.LPCWSTR]
    gdi.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi.SelectObject.restype = wintypes.HGDIOBJ
    gdi.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi.GetGlyphIndicesW.argtypes = [
        wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(wintypes.WORD), wintypes.DWORD,
    ]
    gdi.GetTextFaceW.argtypes = [wintypes.HDC, ctypes.c_int, wintypes.LPWSTR]
    user.GetDC.restype = wintypes.HDC
    user.GetDC.argtypes = [wintypes.HWND]
    user.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    return gdi, user


def missing_glyphs(face: str, text: str) -> str:
    """Characters of ``text`` that the font file ``face`` itself has no glyph for.

    Qt's own checks count fallback fonts, so ask GDI about the font file directly.
    """
    gdi, user = _gdi()
    dc = user.GetDC(None)
    font = gdi.CreateFontW(-14, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 0, 0, face)
    old = gdi.SelectObject(dc, font)
    try:
        actual = ctypes.create_unicode_buffer(64)
        gdi.GetTextFaceW(dc, 64, actual)
        assert actual.value.lower() == face.lower(), f"font {face!r} is not installed"
        chars = [ch for ch in text if not ch.isspace() and ord(ch) <= 0xFFFF]
        buffer = (wintypes.WORD * max(len(chars), 1))()
        gdi.GetGlyphIndicesW(dc, "".join(chars), len(chars), buffer, _GGI_MARK_NONEXISTING_GLYPHS)
        return "".join(ch for ch, glyph in zip(chars, buffer) if glyph == _MISSING)
    finally:
        gdi.SelectObject(dc, old)
        gdi.DeleteObject(font)
        user.ReleaseDC(None, dc)


def _primary_family(widget: QWidget) -> str:
    widget.ensurePolished()
    font = widget.font()
    families = font.families()
    return families[0] if families else font.family()


def _uncovered_texts(root: QWidget) -> list[str]:
    problems: list[str] = []
    widgets = [root, *root.findChildren(QWidget)]
    for widget in widgets:
        texts: list[str] = []
        if isinstance(widget, (QLabel, QAbstractButton)):
            texts.append(widget.text())
        if isinstance(widget, QTabBar):
            texts.extend(widget.tabText(i) for i in range(widget.count()))
        family = _primary_family(widget)
        for text in texts:
            missing = missing_glyphs(family, text)
            if missing:
                problems.append(f"{type(widget).__name__}#{widget.objectName()} {text!r}: {family} lacks {missing!r}")
    app_family = QApplication.font().family()
    for action in root.findChildren(QAction):
        missing = missing_glyphs(app_family, action.text().replace("&", ""))
        if missing:
            problems.append(f"action {action.text()!r}: {app_family} lacks {missing!r}")
    return problems


class _FakeIpc:
    def become_server(self, _on_paths):
        return True

    def close(self) -> None:
        pass


@pytest.fixture
def reader_app(qapp):
    from reader.app import ReaderApp

    original = QApplication.font()
    app = ReaderApp(qapp, ipc=_FakeIpc())
    yield app
    app.close_all()
    QApplication.setFont(original)


def test_missing_glyphs_helper_reads_the_font_file_itself():
    assert missing_glyphs("Segoe UI", "Reader 的") == "的"
    assert missing_glyphs("Microsoft YaHei UI", "Reader 的文件，") == ""
    assert missing_glyphs("Microsoft YaHei UI", "✕") == "✕"


def test_reader_app_uses_a_chinese_capable_ui_font(reader_app):
    from reader.theme import UI_FONT_FAMILY

    assert UI_FONT_FAMILY == "Microsoft YaHei UI"
    assert QApplication.font().family() == UI_FONT_FAMILY


def test_every_window_text_has_glyphs_in_its_own_font(reader_app, qtbot):
    window = reader_app.new_window()
    qtbot.waitExposed(window)
    window.add_untitled_markdown_tab()

    assert _uncovered_texts(window) == []

    window._title_chrome.update_maximize_state(True)
    assert _uncovered_texts(window._title_chrome) == []


def test_browser_toolbar_text_has_glyphs_in_its_own_font(reader_app, qtbot):
    from reader.shell.browser_page import BrowserPage

    window = reader_app.new_window()
    window.add_browser_tab()
    page = window.findChild(BrowserPage)

    assert _uncovered_texts(page) == []


def _multi_family_widgets(root: QWidget) -> list[str]:
    found = []
    for widget in [root, *root.findChildren(QWidget)]:
        widget.ensurePolished()
        families = widget.font().families()
        if len(families) > 1:
            found.append(f"{type(widget).__name__}#{widget.objectName()}: {families}")
    return found


def test_widgets_use_a_single_font_family(reader_app, qtbot):
    # Every extra family in a font list makes Qt build a fallback chain
    # (about 2 s each on first use), even when the first family has every glyph.
    from reader.shell.browser_page import BrowserPage

    window = reader_app.new_window()
    window.add_untitled_markdown_tab()
    window.add_browser_tab()

    assert _multi_family_widgets(window) == []
    assert _multi_family_widgets(window.findChild(BrowserPage)) == []
