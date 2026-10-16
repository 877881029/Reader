from __future__ import annotations

from reader.shell.closed_tabs import MAX_CLOSED, ClosedTabs


def _files(tmp_path, *names):
    paths = []
    for name in names:
        path = tmp_path / name
        path.write_text(name, encoding="utf-8")
        paths.append(path)
    return paths


def test_last_closed_comes_back_first(tmp_path):
    a, b = _files(tmp_path, "a.txt", "b.txt")
    closed = ClosedTabs()
    closed.push(a)
    closed.push(b)

    assert closed.pop() == b.resolve()
    assert closed.pop() == a.resolve()
    assert closed.pop() is None


def test_same_path_is_kept_once_at_the_top(tmp_path):
    a, b = _files(tmp_path, "a.txt", "b.txt")
    closed = ClosedTabs()
    closed.push(a)
    closed.push(b)
    closed.push(a)

    assert closed.pop() == a.resolve()
    assert closed.pop() == b.resolve()
    assert closed.pop() is None


def test_list_is_capped(tmp_path):
    paths = _files(tmp_path, *[f"{i}.txt" for i in range(MAX_CLOSED + 5)])
    closed = ClosedTabs()
    for path in paths:
        closed.push(path)

    popped = []
    while (item := closed.pop()) is not None:
        popped.append(item)

    assert MAX_CLOSED == 20
    assert popped == [p.resolve() for p in reversed(paths[-MAX_CLOSED:])]


def test_deleted_files_are_skipped(tmp_path):
    a, b = _files(tmp_path, "a.txt", "b.txt")
    closed = ClosedTabs()
    closed.push(a)
    closed.push(b)
    b.unlink()

    assert closed.pop() == a.resolve()
    assert closed.pop() is None


def test_missing_or_relative_paths_are_not_recorded(tmp_path):
    closed = ClosedTabs()
    closed.push(tmp_path / "never-existed.txt")
    closed.push(tmp_path)

    assert closed.pop() is None
