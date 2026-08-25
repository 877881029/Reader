from __future__ import annotations

import time
from pathlib import Path

import pytest

from reader.preview.result import PreviewResult


def test_put_get_roundtrip_html(tmp_path: Path):
    from reader.preview.cache import PreviewCache

    src = tmp_path / "a.md"
    src.write_text("hi", encoding="utf-8")
    cache = PreviewCache(tmp_path / "c")
    result = PreviewResult(html="<p>hi</p>", status_label="内置预览")
    cache.put(src, "builtin", result)

    got = cache.get(src, "builtin")
    assert got is not None
    assert got.kind == "html"
    assert got.html == "<p>hi</p>"
    assert got.status_label == "内置预览"


def test_put_get_roundtrip_pdf(tmp_path: Path):
    from reader.preview.cache import PreviewCache

    src = tmp_path / "a.docx"
    src.write_text("doc", encoding="utf-8")
    produced_pdf = tmp_path / "rendered.pdf"
    produced_pdf.write_bytes(b"%PDF-1.4\nfake\n")
    cache = PreviewCache(tmp_path / "c")

    cache.put(
        src,
        "office",
        PreviewResult(html="", status_label="Office 预览", kind="pdf", pdf_path=produced_pdf),
    )

    got = cache.get(src, "office")
    assert got is not None
    assert got.kind == "pdf"
    assert got.pdf_path is not None
    assert got.pdf_path.exists()
    assert got.pdf_path.read_bytes() == b"%PDF-1.4\nfake\n"


def test_pdf_miss_when_cached_pdf_missing(tmp_path: Path):
    from reader.preview.cache import PreviewCache

    src = tmp_path / "a.docx"
    src.write_text("doc", encoding="utf-8")
    produced_pdf = tmp_path / "rendered.pdf"
    produced_pdf.write_bytes(b"%PDF-1.4\nfake\n")
    cache = PreviewCache(tmp_path / "c")
    cache.put(
        src,
        "office",
        PreviewResult(html="", status_label="Office 预览", kind="pdf", pdf_path=produced_pdf),
    )

    slot = cache._slot(cache._key(src, "office"))
    (slot / "preview.pdf").unlink()
    assert cache.get(src, "office") is None


def test_pdf_miss_when_cached_pdf_is_empty(tmp_path: Path):
    from reader.preview.cache import PreviewCache

    src = tmp_path / "a.docx"
    src.write_text("doc", encoding="utf-8")
    produced_pdf = tmp_path / "rendered.pdf"
    produced_pdf.write_bytes(b"%PDF-1.4\nfake\n")
    cache = PreviewCache(tmp_path / "c")
    cache.put(
        src,
        "office",
        PreviewResult(html="", status_label="Office 预览", kind="pdf", pdf_path=produced_pdf),
    )

    slot = cache._slot(cache._key(src, "office"))
    (slot / "preview.pdf").write_bytes(b"")
    assert cache.get(src, "office") is None


def test_pdf_miss_when_cached_pdf_is_tampered(tmp_path: Path):
    from reader.preview.cache import PreviewCache

    src = tmp_path / "a.docx"
    src.write_text("doc", encoding="utf-8")
    produced_pdf = tmp_path / "rendered.pdf"
    produced_pdf.write_bytes(b"%PDF-1.4\nfake\n")
    cache = PreviewCache(tmp_path / "c")
    cache.put(
        src,
        "office",
        PreviewResult(html="", status_label="Office 预览", kind="pdf", pdf_path=produced_pdf),
    )

    slot = cache._slot(cache._key(src, "office"))
    (slot / "preview.pdf").write_bytes(b"%PDF-1.4\nev1l\n")
    assert cache.get(src, "office") is None


def test_miss_on_source_change(tmp_path: Path):
    from reader.preview.cache import PreviewCache

    src = tmp_path / "a.md"
    src.write_text("hi", encoding="utf-8")
    cache = PreviewCache(tmp_path / "c")
    cache.put(src, "builtin", PreviewResult(html="1", status_label="内置预览"))

    src.write_text("ho", encoding="utf-8")
    assert cache.get(src, "builtin") is None


def test_strategy_affects_key(tmp_path: Path):
    from reader.preview.cache import PreviewCache

    src = tmp_path / "a.md"
    src.write_text("hi", encoding="utf-8")
    cache = PreviewCache(tmp_path / "c")
    cache.put(src, "builtin", PreviewResult(html="x", status_label="内置预览"))

    assert cache.get(src, "builtin") is not None
    assert cache.get(src, "office") is None


def test_hit_refreshes_lru_order(tmp_path: Path):
    from reader.preview.cache import PreviewCache

    cache = PreviewCache(tmp_path / "c")
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    c = tmp_path / "c.md"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")
    c.write_text("c", encoding="utf-8")

    payload = "y" * 3000
    cache.put(a, "builtin", PreviewResult(html=payload, status_label="内置预览"))
    time.sleep(0.01)
    cache.put(b, "builtin", PreviewResult(html=payload, status_label="内置预览"))
    time.sleep(0.01)
    cache.put(c, "builtin", PreviewResult(html=payload, status_label="内置预览"))
    time.sleep(0.01)

    # 命中 a，使其成为最近使用项
    assert cache.get(a, "builtin") is not None
    cache.enforce_limit(max_bytes=7000)

    assert cache.get(a, "builtin") is not None
    assert cache.get(c, "builtin") is not None
    assert cache.get(b, "builtin") is None


def test_enforce_limit_keeps_accounting_when_oldest_delete_fails(tmp_path: Path, monkeypatch):
    from reader.preview import cache as cache_module
    from reader.preview.cache import PreviewCache

    cache = PreviewCache(tmp_path / "c")
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    c = tmp_path / "c.md"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")
    c.write_text("c", encoding="utf-8")

    payload = "y" * 3000
    cache.put(a, "builtin", PreviewResult(html=payload, status_label="内置预览"))
    time.sleep(0.01)
    cache.put(b, "builtin", PreviewResult(html=payload, status_label="内置预览"))
    time.sleep(0.01)
    cache.put(c, "builtin", PreviewResult(html=payload, status_label="内置预览"))

    lock_slot = cache._slot(cache._key(a, "builtin"))
    slots = [
        lock_slot,
        cache._slot(cache._key(b, "builtin")),
        cache._slot(cache._key(c, "builtin")),
    ]
    sizes = [cache._slot_size(slot) for slot in slots]
    max_bytes = min(sizes) + 100

    real_rmtree = cache_module.shutil.rmtree

    def flaky_rmtree(path, *args, **kwargs):
        if Path(path) == lock_slot:
            raise PermissionError("locked")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(cache_module.shutil, "rmtree", flaky_rmtree)
    cache.enforce_limit(max_bytes=max_bytes)

    assert lock_slot.exists()
    assert not slots[1].exists()
    assert not slots[2].exists()
    actual_total = sum(f.stat().st_size for f in cache.root.rglob("*") if f.is_file())
    assert actual_total <= max_bytes


def test_corrupted_cache_is_miss(tmp_path: Path):
    from reader.preview.cache import PreviewCache

    src = tmp_path / "a.md"
    src.write_text("hi", encoding="utf-8")
    cache = PreviewCache(tmp_path / "c")
    cache.put(src, "builtin", PreviewResult(html="ok", status_label="内置预览"))

    slot = cache._slot(cache._key(src, "builtin"))
    (slot / "meta.json").write_text("{broken-json", encoding="utf-8")

    assert cache.get(src, "builtin") is None


def test_deleted_cache_dir_is_recreated(tmp_path: Path):
    from reader.preview.cache import PreviewCache

    src = tmp_path / "a.md"
    src.write_text("hi", encoding="utf-8")
    root = tmp_path / "c"
    cache = PreviewCache(root)

    root.rmdir()
    cache.put(src, "builtin", PreviewResult(html="ok", status_label="内置预览"))
    assert cache.get(src, "builtin") is not None


def test_put_does_not_modify_source(tmp_path: Path):
    from reader.preview.cache import PreviewCache

    src = tmp_path / "a.md"
    src.write_text("hello", encoding="utf-8")
    before_bytes = src.read_bytes()
    before_stat = src.stat()
    cache = PreviewCache(tmp_path / "c")

    cache.put(src, "builtin", PreviewResult(html="<p>hello</p>", status_label="内置预览"))

    after_bytes = src.read_bytes()
    after_stat = src.stat()
    assert after_bytes == before_bytes
    assert after_stat.st_size == before_stat.st_size


def test_put_rejects_pptx_visual_kind(tmp_path: Path):
    from reader.preview.cache import PreviewCache

    src = tmp_path / "deck.pptx"
    src.write_bytes(b"pptx")
    cache = PreviewCache(tmp_path / "c")

    with pytest.raises(ValueError, match="unsupported preview kind: pptx"):
        cache.put(
            src,
            "visual",
            PreviewResult(
                html="",
                status_label="内置预览（视觉模式）",
                kind="pptx",
                fallback_html="<p>fallback</p>",
            ),
        )
