from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


def test_markdown_text_view_opens_readonly_then_click_enables_edit(qtbot, tmp_path: Path):
    from reader.preview.md_text_view import MarkdownTextView

    path = tmp_path / "note.md"
    path.write_text("# hi\n", encoding="utf-8")
    view = MarkdownTextView()
    qtbot.addWidget(view)
    view.load_path(path)
    view.show()
    qtbot.waitExposed(view)

    assert view.is_editable() is False
    assert view.text() == "# hi\n"
    qtbot.mouseClick(view, Qt.MouseButton.LeftButton)
    assert view.is_editable() is True


def test_markdown_text_view_untitled_starts_editable_and_save_as(qtbot, tmp_path: Path):
    from reader.preview.md_text_view import MarkdownTextView

    view = MarkdownTextView()
    qtbot.addWidget(view)
    view.load_untitled()
    assert view.is_editable() is True
    assert view.path is None
    view._editor.setPlainText("hello")
    assert view.dirty is True
    assert view.display_title() == "*未命名.md"

    target = tmp_path / "saved.md"
    view.save_as(target)
    assert view.path == target.resolve()
    assert view.dirty is False
    assert target.read_text(encoding="utf-8") == "hello"
    assert view.display_title() == "saved.md"


def test_markdown_text_view_save_overwrites(qtbot, tmp_path: Path):
    from reader.preview.md_text_view import MarkdownTextView

    path = tmp_path / "a.md"
    path.write_text("old", encoding="utf-8")
    view = MarkdownTextView()
    qtbot.addWidget(view)
    view.load_path(path, editable=True)
    view._editor.setPlainText("new")
    assert view.save() is True
    assert path.read_text(encoding="utf-8") == "new"
    assert view.dirty is False
