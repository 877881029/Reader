from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from reader.drafts import Draft, DraftStore, default_drafts_dir


def _draft(doc_id: str = "abc123", **overrides) -> Draft:
    values = dict(
        doc_id=doc_id,
        kind="markdown",
        path=None,
        suffix=".md",
        title="未命名.md",
        text="# 草稿\n内容",
        encoding="utf-8",
        bom=False,
        newline="\n",
        lossless=True,
        file_mtime_ns=None,
        file_size=None,
        saved_at=100.0,
    )
    values.update(overrides)
    return Draft(**values)


def test_save_and_load_round_trip(tmp_path):
    store = DraftStore(tmp_path / "drafts")
    draft = _draft(path=tmp_path / "a.md", kind="text", suffix=".txt", newline="\r\n", bom=True, encoding="utf-16")

    store.save(draft)

    assert store.load_all() == [draft]
    assert [p.name for p in (tmp_path / "drafts").iterdir()] == ["abc123.json"]


def test_save_overwrites_atomically_and_load_sorts_by_time(tmp_path):
    store = DraftStore(tmp_path)
    store.save(_draft("later", saved_at=20.0))
    store.save(_draft("first", saved_at=10.0, text="old"))
    store.save(_draft("first", saved_at=10.0, text="new"))

    drafts = store.load_all()

    assert [d.doc_id for d in drafts] == ["first", "later"]
    assert drafts[0].text == "new"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["first.json", "later.json"]


def test_remove_deletes_and_ignores_missing(tmp_path):
    store = DraftStore(tmp_path)
    store.save(_draft("one"))

    store.remove("one")
    store.remove("one")

    assert store.load_all() == []


def test_unreadable_files_are_skipped_and_kept(tmp_path):
    store = DraftStore(tmp_path)
    store.save(_draft("good"))
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    future = json.loads((tmp_path / "good.json").read_text(encoding="utf-8"))
    future["version"] = 99
    (tmp_path / "future.json").write_text(json.dumps(future), encoding="utf-8")

    assert [d.doc_id for d in store.load_all()] == ["good"]
    assert (tmp_path / "broken.json").exists()
    assert (tmp_path / "future.json").exists()


def test_missing_directory_loads_nothing(tmp_path):
    assert DraftStore(tmp_path / "nope").load_all() == []


@pytest.mark.parametrize("bad", ["", "../x", "a/b", "a\\b", "x.json"])
def test_document_ids_cannot_escape_the_directory(tmp_path, bad):
    with pytest.raises(ValueError):
        DraftStore(tmp_path).save(_draft(bad))


def test_file_changed_compares_recorded_stamp(tmp_path):
    target = tmp_path / "notes.md"
    target.write_text("v1", encoding="utf-8")
    stat = target.stat()
    draft = _draft(path=target, file_mtime_ns=stat.st_mtime_ns, file_size=stat.st_size)
    assert draft.file_changed() is False

    target.write_text("version two", encoding="utf-8")
    os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
    assert draft.file_changed() is True

    target.unlink()
    assert draft.file_changed() is True
    assert _draft().file_changed() is False


def test_default_directory_lives_in_reader_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("READER_DATA_DIR", str(tmp_path))
    assert default_drafts_dir() == Path(tmp_path) / "drafts"
