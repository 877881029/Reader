from __future__ import annotations

from datetime import datetime

import pytest

from reader.history import FileHistory, default_history_dir


class Clock:
    def __init__(self, start: float = 1_800_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> Clock:
    return Clock()


def _history(tmp_path, clock, **kwargs) -> FileHistory:
    return FileHistory(tmp_path / "history", clock=clock, **kwargs)


def test_record_copies_current_content_and_lists_newest_first(tmp_path, clock):
    source = tmp_path / "notes.md"
    history = _history(tmp_path, clock)
    source.write_text("v1", encoding="utf-8")
    history.record(source)
    clock.advance(60)
    source.write_text("v2", encoding="utf-8")
    history.record(source)

    versions = history.versions(source)

    assert [v.path.read_text(encoding="utf-8") for v in versions] == ["v2", "v1"]
    assert all(v.path.suffix == ".md" for v in versions)
    assert versions[0].saved_at == datetime.fromtimestamp(clock.now)
    assert versions[0].size == 2
    assert (versions[0].path.parent / "source.txt").read_text(encoding="utf-8") == str(source.resolve())


def test_identical_content_is_not_recorded_twice(tmp_path, clock):
    source = tmp_path / "a.txt"
    source.write_text("same", encoding="utf-8")
    history = _history(tmp_path, clock)

    history.record(source)
    clock.advance(1)
    assert history.record(source) is None

    assert len(history.versions(source)) == 1


def test_missing_and_large_files_are_skipped(tmp_path, clock):
    history = _history(tmp_path, clock, max_bytes=10)
    big = tmp_path / "big.txt"
    big.write_text("x" * 11, encoding="utf-8")

    assert history.record(tmp_path / "missing.txt") is None
    assert history.record(big) is None
    assert history.versions(big) == []


def test_keeps_at_most_max_versions(tmp_path, clock):
    source = tmp_path / "a.txt"
    history = _history(tmp_path, clock, max_versions=3)
    for index in range(5):
        source.write_text(f"v{index}", encoding="utf-8")
        history.record(source)
        clock.advance(10)

    assert [v.path.read_text(encoding="utf-8") for v in history.versions(source)] == ["v4", "v3", "v2"]


def test_versions_older_than_max_age_are_removed(tmp_path, clock):
    source = tmp_path / "a.txt"
    history = _history(tmp_path, clock, max_age_days=30)
    source.write_text("old", encoding="utf-8")
    history.record(source)
    clock.advance(31 * 86400)
    source.write_text("new", encoding="utf-8")
    history.record(source)

    assert [v.path.read_text(encoding="utf-8") for v in history.versions(source)] == ["new"]


def test_different_files_with_same_name_have_separate_histories(tmp_path, clock):
    one = tmp_path / "one" / "a.txt"
    two = tmp_path / "two" / "a.txt"
    for path in (one, two):
        path.parent.mkdir()
        path.write_text(str(path.parent.name), encoding="utf-8")
    history = _history(tmp_path, clock)
    history.record(one)
    history.record(two)

    assert [v.path.read_text(encoding="utf-8") for v in history.versions(one)] == ["one"]
    assert [v.path.read_text(encoding="utf-8") for v in history.versions(two)] == ["two"]


def test_restore_records_current_content_first_then_writes_the_version(tmp_path, clock):
    source = tmp_path / "a.txt"
    history = _history(tmp_path, clock)
    source.write_bytes(b"old\r\n")
    history.record(source)
    clock.advance(5)
    source.write_bytes(b"current")
    old = history.versions(source)[0]
    clock.advance(5)

    history.restore(old)

    assert source.read_bytes() == b"old\r\n"
    assert [v.path.read_bytes() for v in history.versions(source)] == [b"current", b"old\r\n"]


def test_default_directory_lives_in_reader_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("READER_DATA_DIR", str(tmp_path))
    assert default_history_dir() == tmp_path / "history"
