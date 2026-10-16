from __future__ import annotations

from pathlib import Path


def _code(qtbot):
    from reader.preview.code_view import CodeTextView

    view = CodeTextView()
    qtbot.addWidget(view)
    return view


def _markdown(qtbot):
    from reader.preview.md_text_view import MarkdownTextView

    view = MarkdownTextView()
    qtbot.addWidget(view)
    return view


def _type(view, text: str) -> None:
    editor = view.editor() if hasattr(view, "editor") else view._editor
    editor.moveCursor(editor.textCursor().MoveOperation.End)
    editor.insertPlainText(text)


def test_markdown_untitled_draft_state(qtbot):
    view = _markdown(qtbot)
    view.load_untitled()
    _type(view, "# 草稿")

    state = view.draft_state()

    assert state == {
        "kind": "markdown",
        "path": None,
        "suffix": ".md",
        "title": "未命名.md",
        "text": "# 草稿",
        "encoding": "utf-8",
        "bom": False,
        "newline": state["newline"],
        "lossless": True,
    }


def test_markdown_file_draft_keeps_original_format(qtbot, tmp_path: Path):
    path = tmp_path / "notes.md"
    path.write_bytes("\ufeffline1\r\nline2\r\n".encode("utf-8"))
    view = _markdown(qtbot)
    view.load_path(path, editable=True)
    _type(view, "more")

    state = view.draft_state()

    assert state["path"] == path.resolve()
    assert (state["encoding"], state["bom"], state["newline"]) == ("utf-8", True, "\r\n")
    assert state["text"].endswith("more")


def test_markdown_restore_marks_dirty_and_saves_to_original_file(qtbot, tmp_path: Path):
    path = tmp_path / "notes.md"
    path.write_bytes(b"old\r\n")
    view = _markdown(qtbot)

    view.restore_draft(
        kind="markdown", path=path, suffix=".md", title="notes.md", text="restored\nsecond",
        encoding="utf-8", bom=True, newline="\r\n", lossless=True,
    )

    assert view.dirty is True
    assert view.is_editable() is True
    assert view.display_title() == "*notes.md"
    assert view.path == path.resolve()
    assert view.save() is True
    assert path.read_bytes() == "\ufeffrestored\r\nsecond".encode("utf-8")
    assert view.dirty is False


def test_markdown_restore_untitled_keeps_its_title(qtbot):
    view = _markdown(qtbot)

    view.restore_draft(
        kind="markdown", path=None, suffix=".md", title="未命名.md", text="draft",
        encoding="utf-8", bom=False, newline="\n", lossless=True,
    )

    assert view.path is None
    assert view.display_title() == "*未命名.md"
    assert view.text() == "draft"


def test_code_draft_state_and_restore_round_trip(qtbot, tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_bytes(b'{"a": 1}\r\n')
    source = _code(qtbot)
    source.load_path(path)
    _type(source, "\n")
    state = source.draft_state()
    assert state["kind"] == "text"
    assert state["path"] == path.resolve()
    assert state["suffix"] == ".json"
    assert state["newline"] == "\r\n"

    restored = _code(qtbot)
    restored.restore_draft(**{**state, "text": '{"a": 2}'})

    assert restored.dirty is True
    assert restored.is_editable() is True
    assert restored.display_title() == "*config.json"
    assert restored.save() is True
    assert path.read_bytes() == b'{"a": 2}'
    assert restored.dirty is False


def test_code_restore_untitled_text(qtbot):
    view = _code(qtbot)

    view.restore_draft(
        kind="text", path=None, suffix=".txt", title="未命名.txt", text="hello",
        encoding="utf-8", bom=False, newline="\r\n", lossless=True,
    )

    assert view.path is None
    assert view.display_title() == "*未命名.txt"
    assert view.text() == "hello"
