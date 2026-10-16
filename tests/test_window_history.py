from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QFileDialog

from reader.history import FileHistory


@pytest.fixture
def history(tmp_path) -> FileHistory:
    return FileHistory(tmp_path / "history")


def _window(qtbot, history):
    from reader.shell.window import MainWindow

    window = MainWindow(history=history)
    qtbot.addWidget(window)
    window.show()
    return window


def _view(window):
    return window._editable_view(window._documents[window._current_document_id()])


def _type(view, text):
    editor = view.editor()
    editor.moveCursor(editor.textCursor().MoveOperation.End)
    editor.insertPlainText(text)


def _save_dialog(monkeypatch, target: Path):
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_a, **_k: (str(target), ""))


def test_ctrl_s_over_existing_file_keeps_old_content(qtbot, history, tmp_path):
    target = tmp_path / "notes.txt"
    window = _window(qtbot, history)
    window.add_untitled_text_tab()
    view = _view(window)
    _type(view, "first")
    view.save_as(target)
    _type(view, " second")

    assert window.save_current_tab() is True

    assert target.read_text(encoding="utf-8") == "first second"
    assert [v.path.read_text(encoding="utf-8") for v in history.versions(target)] == ["first"]


def test_first_save_of_new_file_records_nothing(qtbot, history, tmp_path, monkeypatch):
    target = tmp_path / "new.txt"
    _save_dialog(monkeypatch, target)
    window = _window(qtbot, history)
    window.add_untitled_text_tab()
    _type(_view(window), "hello")

    assert window.save_current_tab() is True

    assert target.read_text(encoding="utf-8") == "hello"
    assert history.versions(target) == []


def test_save_as_over_existing_file_keeps_its_content(qtbot, history, tmp_path, monkeypatch):
    target = tmp_path / "existing.txt"
    target.write_text("keep me", encoding="utf-8")
    _save_dialog(monkeypatch, target)
    window = _window(qtbot, history)
    window.add_untitled_text_tab()
    _type(_view(window), "replacement")

    assert window.save_current_tab_as() is True

    assert target.read_text(encoding="utf-8") == "replacement"
    assert [v.path.read_text(encoding="utf-8") for v in history.versions(target)] == ["keep me"]


def test_window_without_history_still_saves(qtbot, tmp_path):
    target = tmp_path / "plain.txt"
    window = _window(qtbot, None)
    window.add_untitled_text_tab()
    view = _view(window)
    _type(view, "a")
    view.save_as(target)
    _type(view, "b")

    assert window.save_current_tab() is True
    assert target.read_text(encoding="utf-8") == "ab"


def test_reader_app_provides_history_in_data_dir(qapp, monkeypatch, tmp_path):
    from reader.app import ReaderApp

    class Ipc:
        def become_server(self, _cb):
            return True

        def close(self):
            pass

    monkeypatch.setenv("READER_DATA_DIR", str(tmp_path / "data"))
    app = ReaderApp(qapp, ipc=Ipc())
    try:
        window = app.new_window()
        assert window._history.root == tmp_path / "data" / "history"
    finally:
        app.close_all()
