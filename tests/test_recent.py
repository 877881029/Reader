from pathlib import Path

from reader.shell.recent import load_recent, remember_recent, visible_recent


def test_remember_recent_prepends_dedupes_and_caps(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("READER_DATA_DIR", str(tmp_path / "data"))
    files = []
    for index in range(14):
        path = tmp_path / f"note-{index}.md"
        path.write_text("x", encoding="utf-8")
        files.append(path)
        remember_recent(path)

    loaded = load_recent()
    assert loaded[0] == files[-1].resolve()
    assert len(loaded) == 12
    assert files[0].resolve() not in loaded
    remember_recent(files[5])
    assert load_recent()[0] == files[5].resolve()
    assert load_recent().count(files[5].resolve()) == 1


def test_remember_recent_skips_untitled_drafts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("READER_DATA_DIR", str(tmp_path / "data"))
    remember_recent(Path("未命名-abcd1234.md"))
    assert load_recent() == []


def test_visible_recent_drops_missing_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("READER_DATA_DIR", str(tmp_path / "data"))
    alive = tmp_path / "alive.md"
    missing = tmp_path / "gone.md"
    alive.write_text("ok", encoding="utf-8")
    missing.write_text("bye", encoding="utf-8")
    remember_recent(missing)
    remember_recent(alive)
    missing.unlink()

    shown = visible_recent()
    assert shown == [alive.resolve()]
    assert load_recent() == [alive.resolve()]
