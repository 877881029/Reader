from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

from reader.drafts import DraftStore
from reader.preview.result import PreviewResult


def _window(qtbot, store):
    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=lambda *_a, **_k: PreviewResult(html="x", status_label="内置预览"),
        drafts=store,
    )
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


@pytest.fixture
def store(tmp_path) -> DraftStore:
    return DraftStore(tmp_path / "drafts")


def _current_view(window):
    return window._editable_view(window._documents[window._current_document_id()])


def _editor(view):
    return view.editor() if hasattr(view, "editor") else view._editor


def _type(view, text: str) -> None:
    editor = _editor(view)
    editor.moveCursor(editor.textCursor().MoveOperation.End)
    editor.insertPlainText(text)


def test_draft_is_written_about_a_second_after_editing(qtbot, store):
    from reader.shell.window import DRAFT_SAVE_DELAY_MS

    window = _window(qtbot, store)
    window.add_untitled_markdown_tab()
    _type(_current_view(window), "# 草稿")

    assert store.load_all() == []
    assert window._draft_timer.interval() == DRAFT_SAVE_DELAY_MS == 1000
    qtbot.waitUntil(lambda: len(store.load_all()) == 1, timeout=5000)
    draft = store.load_all()[0]
    assert draft.doc_id == window._current_document_id()
    assert (draft.kind, draft.text, draft.path, draft.title) == ("markdown", "# 草稿", None, "未命名.md")


def test_deactivating_the_window_writes_pending_drafts_at_once(qtbot, store):
    window = _window(qtbot, store)
    window.add_untitled_text_tab()
    _type(_current_view(window), "hello")

    QApplication.sendEvent(window, QEvent(QEvent.Type.WindowDeactivate))

    assert [d.text for d in store.load_all()] == ["hello"]


def test_undo_back_to_clean_removes_the_draft(qtbot, store):
    window = _window(qtbot, store)
    window.add_untitled_text_tab()
    view = _current_view(window)
    _type(view, "x")
    window.flush_drafts()
    assert len(store.load_all()) == 1

    _editor(view).undo()
    window.flush_drafts()

    assert view.dirty is False
    assert store.load_all() == []


def test_saving_removes_the_draft_and_later_edits_record_the_file_stamp(qtbot, store, tmp_path):
    window = _window(qtbot, store)
    window.add_untitled_text_tab()
    view = _current_view(window)
    _type(view, "first")
    window.flush_drafts()
    target = tmp_path / "saved.txt"

    view.save_as(target)
    window.flush_drafts()
    assert store.load_all() == []

    _type(view, " second")
    window.flush_drafts()
    draft = store.load_all()[0]
    assert draft.path == target.resolve()
    assert draft.file_mtime_ns == target.stat().st_mtime_ns
    assert draft.file_size == target.stat().st_size
    assert draft.file_changed() is False


def test_closing_a_tab_removes_its_draft(qtbot, store):
    window = _window(qtbot, store)
    window.add_untitled_text_tab()
    window.add_untitled_text_tab()
    _type(_current_view(window), "discard me")
    window.flush_drafts()

    window.close_tab(window._tabs.currentIndex())

    assert store.load_all() == []


def test_normal_window_close_removes_drafts(qtbot, store):
    window = _window(qtbot, store)
    window.add_untitled_text_tab()
    _type(_current_view(window), "bye")
    window.flush_drafts()

    window.close()

    assert store.load_all() == []


def test_window_without_store_still_edits(qtbot):
    window = _window(qtbot, None)
    window.add_untitled_text_tab()
    _type(_current_view(window), "no drafts")
    window.flush_drafts()

    assert window._draft_timer is None


def test_moved_tab_keeps_one_draft_with_latest_text(qtbot, store):
    from reader.shell.window import MainWindow

    source = _window(qtbot, store)
    target = MainWindow(drafts=store, executor=source._executor)
    qtbot.addWidget(target)
    target.show()
    source.add_untitled_text_tab()
    source.add_untitled_markdown_tab()
    view = _current_view(source)
    document_id = source._current_document_id()
    _type(view, "one")

    assert source.move_document_to(document_id, target) is True
    _type(view, " two")
    target.flush_drafts()
    source.flush_drafts()

    drafts = store.load_all()
    assert [(d.doc_id, d.text) for d in drafts] == [(document_id, "one two")]
