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
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"x")

    d = decide_open([], [missing, pdf])

    assert d.to_open == ()
    assert d.to_focus is None
    assert d.rejected == (
        (missing, "not_found"),
        (pdf, "unsupported_extension"),
    )
