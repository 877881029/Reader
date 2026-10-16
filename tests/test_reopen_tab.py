from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QLabel

from reader.preview.result import PreviewResult


def _stub_preview(window) -> None:
    window._preview_fn = lambda source, office=None, mode="builtin": PreviewResult(
        html=source.name, status_label="内置预览"
    )
    window._viewer_factory = lambda result, _path=None: QLabel(result.html)


class _Cache:
    def get(self, *_args):
        return None

    def put(self, *_args):
        return None


class FakeIpc:
    def become_server(self, _on_paths):
        return True

    def close(self) -> None:
        pass


@pytest.fixture
def files(tmp_path) -> list[Path]:
    paths = []
    for name in ("a.txt", "b.txt"):
        path = tmp_path / name
        path.write_text(name, encoding="utf-8")
        paths.append(path)
    return paths


@pytest.fixture
def app(qapp, monkeypatch):
    from reader.app import ReaderApp

    reader_app = ReaderApp(qapp, ipc=FakeIpc(), drafts=None)
    real_new_window = reader_app.new_window

    def new_window(**kwargs):
        window = real_new_window(**kwargs)
        _stub_preview(window)
        window._cache_factory = _Cache
        return window

    monkeypatch.setattr(reader_app, "new_window", new_window)
    yield reader_app
    reader_app.close_all()


def _titles(window) -> list[str]:
    return [window.tab_title(i) for i in range(window.tab_count())]


def test_shortcut_is_ctrl_shift_t(app):
    window = app.new_window()
    assert window.actionReopenClosedTab.shortcut().toString() == "Ctrl+Shift+T"


def test_closed_file_tab_comes_back(app, files):
    window = app.new_window()
    window.open_paths([str(p) for p in files])
    window.close_tab(1)
    assert _titles(window) == ["a.txt"]

    window.actionReopenClosedTab.trigger()

    assert _titles(window) == ["a.txt", "b.txt"]
    assert window._tabs.currentIndex() == 1


def test_untitled_draft_is_not_recorded(app):
    window = app.new_window()
    window.add_untitled_text_tab()
    window.add_untitled_markdown_tab()
    window.close_tab(1)

    window.actionReopenClosedTab.trigger()

    assert window.tab_count() == 1
    assert window.status_text() == "没有可重新打开的标签"


def test_tabs_of_a_closed_window_can_be_reopened_elsewhere(app, files):
    first = app.new_window()
    first.open_paths([str(p) for p in files])
    second = app.new_window()

    first.close()
    second.reopen_closed_tab()
    second.reopen_closed_tab()

    assert _titles(second) == ["b.txt", "a.txt"]


def test_file_open_in_another_window_is_focused_not_duplicated(app, files):
    a = files[0]
    first = app.new_window()
    first.open_paths([str(a), str(files[1])])
    first.close_tab(0)
    third = app.new_window()
    third.open_paths([str(files[1]), str(a)])
    third._tabs.setCurrentIndex(0)
    second = app.new_window()

    second.reopen_closed_tab()

    assert second.tab_count() == 0
    assert third.tab_count() == 2
    assert third.tab_title(third._tabs.currentIndex()) == "a.txt"


def test_tab_menu_offers_reopen(app, files):
    window = app.new_window()
    window.open_paths([str(files[0])])
    actions = [a.text() for a in window._build_tab_menu(0).actions()]
    assert "重新打开关闭的标签" in actions
