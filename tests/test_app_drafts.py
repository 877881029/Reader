from __future__ import annotations

from pathlib import Path

import pytest

from reader.drafts import Draft, DraftStore


class FakeIpc:
    def __init__(self, primary: bool = True) -> None:
        self.primary = primary

    def become_server(self, _on_paths):
        return self.primary

    def close(self) -> None:
        pass


def _draft(doc_id: str, **overrides) -> Draft:
    values = dict(
        doc_id=doc_id, kind="markdown", path=None, suffix=".md", title="未命名.md",
        text="# 草稿", encoding="utf-8", bom=False, newline="\n", lossless=True,
        file_mtime_ns=None, file_size=None, saved_at=1.0,
    )
    values.update(overrides)
    return Draft(**values)


@pytest.fixture
def store(tmp_path) -> DraftStore:
    return DraftStore(tmp_path / "drafts")


@pytest.fixture
def make_app(qapp):
    from reader.app import ReaderApp

    apps = []

    def make(**kwargs):
        app = ReaderApp(qapp, ipc=FakeIpc(kwargs.pop("primary", True)), **kwargs)
        apps.append(app)
        return app

    yield make
    for app in apps:
        app.close_all()


def _titles(window) -> list[str]:
    return [window.tab_title(i) for i in range(window.tab_count())]


def test_first_window_restores_drafts_without_asking(make_app, store, tmp_path):
    notes = tmp_path / "notes.txt"
    notes.write_text("saved", encoding="utf-8")
    stat = notes.stat()
    store.save(_draft("old1", saved_at=1.0))
    store.save(_draft("old2", kind="text", path=notes, suffix=".txt", title="notes.txt",
                      text="unsaved change", newline="\r\n",
                      file_mtime_ns=stat.st_mtime_ns, file_size=stat.st_size, saved_at=2.0))
    app = make_app(drafts=store)

    window = app.new_window()

    assert _titles(window) == ["*未命名.md", "*notes.txt"]
    assert "已恢复 2 个未保存的标签" in window.status_text()
    assert "在别处修改" not in window.status_text()
    restored = store.load_all()
    assert sorted(d.text for d in restored) == ["# 草稿", "unsaved change"]
    assert not {"old1", "old2"} & {d.doc_id for d in restored}
    view = window._editable_view(window._documents[window._current_document_id()])
    assert view.path == notes.resolve()
    assert view.save() is True
    assert notes.read_bytes() == b"unsaved change"


def test_restore_reports_files_changed_elsewhere(make_app, store, tmp_path):
    notes = tmp_path / "notes.txt"
    notes.write_text("saved", encoding="utf-8")
    store.save(_draft("old", kind="text", path=notes, suffix=".txt", title="notes.txt",
                      text="mine", file_mtime_ns=1, file_size=1))

    window = make_app(drafts=store).new_window()

    assert "1 个原文件已在别处修改" in window.status_text()


def test_only_the_first_window_restores(make_app, store):
    store.save(_draft("old"))
    app = make_app(drafts=store)

    first = app.new_window()
    second = app.new_window()

    assert first.tab_count() == 1
    assert second.tab_count() == 0


def test_secondary_instance_does_not_touch_drafts(make_app, store):
    store.save(_draft("old"))

    app = make_app(drafts=store, primary=False)

    assert app._restore_queue == []
    assert [d.doc_id for d in store.load_all()] == ["old"]


def test_session_end_saves_drafts_and_closes_without_asking(make_app, store):
    app = make_app(drafts=store)
    window = app.new_window()
    window.unsaved_prompt = lambda _name: pytest.fail("must not ask during sign-out")
    window.add_untitled_text_tab()
    view = window._editable_view(window._documents[window._current_document_id()])
    editor = view.editor()
    editor.insertPlainText("keep me")

    app._on_commit_data(None)
    window.close()

    assert window.is_closing() is True
    assert [d.text for d in store.load_all()] == ["keep me"]


def test_default_store_lives_in_the_data_dir(make_app, monkeypatch, tmp_path):
    monkeypatch.setenv("READER_DATA_DIR", str(tmp_path / "data"))

    app = make_app()

    assert app._drafts.directory == Path(tmp_path / "data" / "drafts")
