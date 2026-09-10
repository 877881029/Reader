from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QLabel, QPlainTextEdit

from reader.preview.find_support import find_in_widget
from reader.preview.md_text_view import MarkdownTextView
from reader.shell.find_bar import FindBar
from reader.theme import CHROME, PAPER


def test_plain_text_find_wraps_and_respects_case(qtbot):
    editor = QPlainTextEdit()
    qtbot.addWidget(editor)
    editor.setPlainText("Alpha alpha ALPHA")
    editor.moveCursor(editor.textCursor().MoveOperation.Start)

    first = find_in_widget(editor, "alpha", forward=True, case_sensitive=False)
    assert first.found is True
    assert editor.textCursor().selectedText() == "Alpha"

    second = find_in_widget(editor, "alpha", forward=True, case_sensitive=False)
    assert second.found is True
    assert editor.textCursor().selectedText() == "alpha"

    third = find_in_widget(editor, "alpha", forward=True, case_sensitive=False)
    assert third.found is True
    assert editor.textCursor().selectedText() == "ALPHA"

    wrapped = find_in_widget(editor, "alpha", forward=True, case_sensitive=False)
    assert wrapped.found is True
    assert editor.textCursor().selectedText() == "Alpha"

    missing_case = find_in_widget(editor, "alpha", forward=True, case_sensitive=True)
    assert missing_case.found is True
    assert editor.textCursor().selectedText() == "alpha"

    absent = find_in_widget(editor, "nope", forward=True, case_sensitive=False)
    assert absent.found is False


def test_label_find_matches_substring_case_insensitive():
    label = QLabel("Hello Reader")
    assert find_in_widget(label, "reader", case_sensitive=False).found is True
    assert find_in_widget(label, "reader", case_sensitive=True).found is False
    assert find_in_widget(label, "missing").found is False


def test_find_bar_uses_paper_tokens(qtbot):
    bar = FindBar()
    qtbot.addWidget(bar)
    sheet = bar.styleSheet().replace(" ", "").lower()
    assert PAPER.lower() in sheet
    assert CHROME.lower() in sheet
    assert bar.objectName() == "findBar"


def test_ctrl_f_ignored_on_welcome(qtbot):
    from reader.shell.window import MainWindow

    window = MainWindow(preview_fn=lambda *_args, **_kwargs: None)
    qtbot.addWidget(window)
    window.show()
    assert window.tab_count() == 0
    window.actionFind.trigger()
    assert window.find_bar().isVisible() is False


def test_ctrl_f_finds_next_in_markdown_and_escape_closes(qtbot):
    from reader.shell.window import MainWindow

    window = MainWindow(preview_fn=lambda *_a, **_k: None)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.add_untitled_markdown_tab()
    view = window.findChild(MarkdownTextView)
    assert view is not None
    view._editor.setPlainText("one two one")
    assert window.actionFind.shortcut().matches(
        QKeySequence(QKeySequence.StandardKey.Find)
    ) == QKeySequence.SequenceMatch.ExactMatch

    window.actionFind.trigger()
    bar = window.find_bar()
    assert bar.isVisible() is True
    bar.set_query("one")
    bar.find_next()
    assert view._editor.textCursor().selectedText() == "one"
    start = view._editor.textCursor().selectionStart()
    bar.find_next()
    assert view._editor.textCursor().selectedText() == "one"
    assert view._editor.textCursor().selectionStart() != start
    assert bar.not_found_visible() is False

    bar.set_query("missing")
    bar.find_next()
    assert bar.not_found_visible() is True

    qtbot.keyClick(bar.query_edit(), Qt.Key.Key_Escape)
    assert bar.isVisible() is False
