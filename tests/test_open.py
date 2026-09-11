from pathlib import Path

from reader.open import decide_open


def test_opens_new_supported_file(tmp_path: Path):
    p = tmp_path / "a.md"
    p.write_text("x", encoding="utf-8")

    d = decide_open([], [p])

    assert d.to_open == (p.resolve(),)
    assert d.to_focus is None
    assert d.rejected == ()


def test_focuses_existing_same_path_after_normalization(tmp_path: Path):
    p = tmp_path / "a.md"
    p.write_text("x", encoding="utf-8")

    d = decide_open([p.resolve()], [tmp_path / "." / "a.md"])

    assert d.to_open == ()
    assert d.to_focus == p.resolve()
    assert d.rejected == ()


def test_opens_new_files_in_order_and_focuses_duplicate(tmp_path: Path):
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    c = tmp_path / "c.md"
    for p in (a, b, c):
        p.write_text("x", encoding="utf-8")

    d = decide_open([], [a, b, a, c, b])

    assert d.to_open == (a.resolve(), b.resolve(), c.resolve())
    assert d.to_focus == b.resolve()
    assert d.rejected == ()


def test_rejected_items_keep_reason_and_order(tmp_path: Path):
    missing = tmp_path / "missing.md"
    exe = tmp_path / "a.exe"
    exe.write_bytes(b"x")

    d = decide_open([], [missing, exe])

    assert d.to_open == ()
    assert d.to_focus is None
    assert d.rejected == (
        (missing, "not_found"),
        (exe, "unsupported_extension"),
    )


def test_opens_json_yaml_xml(tmp_path: Path):
    files = [
        tmp_path / "a.json",
        tmp_path / "b.yaml",
        tmp_path / "c.yml",
        tmp_path / "d.xml",
    ]
    for path in files:
        path.write_text("x", encoding="utf-8")

    d = decide_open([], files)

    assert d.to_open == tuple(path.resolve() for path in files)
    assert d.rejected == ()


def test_opens_svg(tmp_path: Path):
    path = tmp_path / "icon.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"/>',
        encoding="utf-8",
    )
    d = decide_open([], [path])
    assert d.to_open == (path.resolve(),)
    assert d.rejected == ()
