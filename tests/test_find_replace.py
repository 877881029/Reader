from __future__ import annotations

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

from reader.preview.find_support import replace_all, replace_current


def _editor(qtbot, text: str) -> QPlainTextEdit:
    editor = QPlainTextEdit()
    qtbot.addWidget(editor)
    editor.setPlainText(text)
    editor.document().setModified(False)
    return editor


def _select(editor: QPlainTextEdit, start: int, end: int) -> None:
    cursor = editor.textCursor()
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)


def test_replace_current_without_matching_selection_only_finds(qtbot):
    editor = _editor(qtbot, "cat Cat cat")

    assert replace_current(editor, "cat", "dog", case_sensitive=True) is True

    assert editor.toPlainText() == "cat Cat cat"
    assert editor.textCursor().selectedText() == "cat"


def test_replace_current_replaces_selection_then_advances(qtbot):
    editor = _editor(qtbot, "cat Cat cat")
    _select(editor, 0, 3)

    assert replace_current(editor, "cat", "dog", case_sensitive=True) is True

    assert editor.toPlainText() == "dog Cat cat"
    assert editor.textCursor().selectionStart() == 8
    assert editor.document().isModified()


def test_replace_current_case_insensitive_matches_selection(qtbot):
    editor = _editor(qtbot, "Cat")
    _select(editor, 0, 3)

    assert replace_current(editor, "cat", "dog", case_sensitive=False) is False

    assert editor.toPlainText() == "dog"


def test_replace_all_counts_honours_case_and_is_one_undo_step(qtbot):
    editor = _editor(qtbot, "a A a\na")

    assert replace_all(editor, "a", "bb", case_sensitive=True) == 3
    assert editor.toPlainText() == "bb A bb\nbb"
    editor.undo()
    assert editor.toPlainText() == "a A a\na"

    assert replace_all(editor, "a", "x", case_sensitive=False) == 4
    assert editor.toPlainText() == "x x x\nx"


def test_replace_all_handles_replacement_containing_query(qtbot):
    editor = _editor(qtbot, "ab ab")

    assert replace_all(editor, "ab", "abab", case_sensitive=True) == 2
    assert editor.toPlainText() == "abab abab"


def test_replace_refuses_read_only_editor(qtbot):
    editor = _editor(qtbot, "cat")
    editor.setReadOnly(True)
    _select(editor, 0, 3)

    assert replace_all(editor, "cat", "dog", case_sensitive=True) == 0
    assert replace_current(editor, "cat", "dog", case_sensitive=True) is False
    assert editor.toPlainText() == "cat"
