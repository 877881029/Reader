from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QPushButton

from reader.history import FileHistory


@pytest.fixture
def history(tmp_path) -> FileHistory:
    return FileHistory(tmp_path / "history")


@pytest.fixture
def notes(tmp_path, history) -> Path:
    path = tmp_path / "notes.txt"
    path.write_text("v1", encoding="utf-8")
    history.record(path)
    path.write_text("v2 now", encoding="utf-8")
    return path


def _window(qtbot, history, path: Path):
    from reader.shell.window import MainWindow

    window = MainWindow(history=history)
    qtbot.addWidget(window)
    window.show()
    window.open_paths([str(path)])
    qtbot.waitUntil(
        lambda: window._editable_view(window._documents[window._current_document_id()]) is not None,
        timeout=15_000,
    )
    return window


def _history_menu(window, index: int = 0):
    menu = window._build_tab_menu(index)
    entry = next(a for a in menu.actions() if a.text() == "历史版本")
    return entry.menu()


def _view_at(window, index: int):
    page = window._tabs.widget(index)
    document = next(d for d in window._documents.values() if d.page is page)
    from reader.preview.code_view import CodeTextView

    return document, page.findChild(CodeTextView)


def test_tab_menu_lists_versions(qtbot, history, notes):
    window = _window(qtbot, history, notes)

    entries = _history_menu(window).actions()

    version = history.versions(notes)[0]
    assert [a.text() for a in entries] == [f"{version.saved_at:%m-%d %H:%M:%S} · 2 B"]


def test_file_without_history_shows_disabled_entry(qtbot, history, tmp_path):
    fresh = tmp_path / "fresh.txt"
    fresh.write_text("x", encoding="utf-8")
    window = _window(qtbot, history, fresh)

    entries = _history_menu(window).actions()

    assert [(a.text(), a.isEnabled()) for a in entries] == [("没有历史版本", False)]


def test_opening_a_version_shows_it_read_only(qtbot, history, notes):
    window = _window(qtbot, history, notes)
    version = history.versions(notes)[0]

    _history_menu(window).actions()[0].trigger()

    assert window.tab_count() == 2
    assert window.tab_title(1) == f"notes.txt · {version.saved_at:%m-%d %H:%M}"
    document, view = _view_at(window, 1)
    assert view.text() == "v1"
    assert view.is_editable() is False
    assert window._editable_view(document) is None
    assert window.actionSave.isEnabled() is False
    assert window._tabs.widget(1).findChild(QPushButton, "historyRestoreButton").text() == "恢复为此版本"


def test_restore_writes_back_and_reloads_the_open_tab(qtbot, history, notes):
    window = _window(qtbot, history, notes)
    _history_menu(window).actions()[0].trigger()

    window._tabs.widget(1).findChild(QPushButton, "historyRestoreButton").click()

    assert notes.read_text(encoding="utf-8") == "v1"
    assert [v.path.read_text(encoding="utf-8") for v in history.versions(notes)] == ["v2 now", "v1"]
    _document, original = _view_at(window, 0)
    assert original.text() == "v1"
    assert original.dirty is False
    assert "已恢复" in window.status_text()


def test_restore_refuses_while_the_file_has_unsaved_edits(qtbot, history, notes):
    window = _window(qtbot, history, notes)
    _document, original = _view_at(window, 0)
    original.editor().insertPlainText("typing ")
    _history_menu(window).actions()[0].trigger()

    window._tabs.widget(1).findChild(QPushButton, "historyRestoreButton").click()

    assert notes.read_text(encoding="utf-8") == "v2 now"
    assert "未保存" in window.status_text()
