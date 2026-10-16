from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from reader.preview import link_click
from reader.preview.link_click import url_at


@pytest.mark.parametrize(
    ("text", "column", "expected"),
    [
        ("see https://example.com/a?b=1 now", 10, "https://example.com/a?b=1"),
        ("end https://example.com/x.", 8, "https://example.com/x"),
        ("中文 https://example.com/页面，后面", 6, "https://example.com/页面"),
        ("（链接 http://example.com/x）", 6, "http://example.com/x"),
        ("wiki (https://en.wikipedia.org/wiki/Foo_(bar)) ok", 10, "https://en.wikipedia.org/wiki/Foo_(bar)"),
        ('"https://example.com/q"', 3, "https://example.com/q"),
        ("see https://example.com now", 1, None),
        ("ftp://example.com/file", 3, None),
        ("javascript:alert(1)", 3, None),
        ("http:// nothing", 2, None),
    ],
)
def test_url_at(text, column, expected):
    assert url_at(text, column) == expected


@pytest.fixture
def opened(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(link_click, "open_url", calls.append)
    return calls


def _point_of(editor, offset: int) -> QPoint:
    cursor = editor.textCursor()
    cursor.setPosition(offset)
    rect = editor.cursorRect(cursor)
    return QPoint(rect.right() + 3, rect.center().y())


def _code_view(qtbot, text: str):
    from reader.preview.code_view import CodeTextView

    view = CodeTextView()
    qtbot.addWidget(view)
    view.load_text(text, ".txt")
    view.resize(700, 300)
    view.show()
    qtbot.waitExposed(view)
    return view, view.editor()


def _markdown_view(qtbot, tmp_path, text: str):
    from reader.preview.md_text_view import MarkdownTextView

    path = tmp_path / "links.md"
    path.write_text(text, encoding="utf-8")
    view = MarkdownTextView()
    qtbot.addWidget(view)
    view.load_path(path)
    view.resize(700, 300)
    view.show()
    qtbot.waitExposed(view)
    return view, view._editor


TEXT = "visit https://example.com/path now"
URL_OFFSET = TEXT.index("example")


def test_ctrl_click_on_url_in_code_view_opens_it(qtbot, opened):
    _view, editor = _code_view(qtbot, TEXT)

    QTest.mouseClick(editor.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, _point_of(editor, URL_OFFSET))

    assert opened == ["https://example.com/path"]


def test_plain_click_and_ctrl_click_outside_url_do_not_open(qtbot, opened):
    _view, editor = _code_view(qtbot, TEXT)

    QTest.mouseClick(editor.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, _point_of(editor, URL_OFFSET))
    QTest.mouseClick(editor.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, _point_of(editor, 1))

    assert opened == []


def test_ctrl_hover_shows_hand_cursor_and_underline(qtbot, opened):
    _view, editor = _code_view(qtbot, TEXT)
    viewport = editor.viewport()

    QTest.mouseMove(viewport, _point_of(editor, URL_OFFSET))
    assert viewport.cursor().shape() != Qt.CursorShape.PointingHandCursor

    link_click.LinkClicker.hover(editor, _point_of(editor, URL_OFFSET), ctrl=True)
    assert viewport.cursor().shape() == Qt.CursorShape.PointingHandCursor
    underlined = [s for s in editor.extraSelections() if s.format.fontUnderline()]
    assert len(underlined) == 1
    cursor = underlined[0].cursor
    assert cursor.selectedText() == "https://example.com/path"

    link_click.LinkClicker.hover(editor, _point_of(editor, URL_OFFSET), ctrl=False)
    assert viewport.cursor().shape() != Qt.CursorShape.PointingHandCursor
    assert not [s for s in editor.extraSelections() if s.format.fontUnderline()]


def test_code_view_keeps_current_line_highlight_with_link_underline(qtbot, opened):
    _view, editor = _code_view(qtbot, TEXT)
    before = len(editor.extraSelections())

    link_click.LinkClicker.hover(editor, _point_of(editor, URL_OFFSET), ctrl=True)

    assert len(editor.extraSelections()) == before + 1


def test_ctrl_click_in_markdown_editor_opens_url_without_entering_edit_mode(qtbot, tmp_path, opened):
    view, editor = _markdown_view(qtbot, tmp_path, TEXT)
    assert view.is_editable() is False

    QTest.mouseClick(editor.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, _point_of(editor, URL_OFFSET))

    assert opened == ["https://example.com/path"]
    assert view.is_editable() is False


def test_editing_still_places_cursor_on_plain_click(qtbot, tmp_path, opened):
    view, editor = _markdown_view(qtbot, tmp_path, TEXT)
    view.enable_editing()

    QTest.mouseClick(editor.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, _point_of(editor, URL_OFFSET))

    assert opened == []
    assert abs(editor.textCursor().position() - (URL_OFFSET + 1)) <= 1
    assert editor.textCursor().selectionStart() == editor.textCursor().position()
