from __future__ import annotations

from pathlib import Path

import pytest

from reader import text_io
from reader.text_io import TextFile, default_text_file, read_text_file, write_text_file

SAMPLE = "第一行 hello\n第二行 world\n"


@pytest.mark.parametrize(
    ("raw", "encoding", "bom", "newline"),
    [
        (SAMPLE.encode("utf-8"), "utf-8", False, "\n"),
        (SAMPLE.replace("\n", "\r\n").encode("utf-8"), "utf-8", False, "\r\n"),
        (b"\xef\xbb\xbf" + SAMPLE.replace("\n", "\r\n").encode("utf-8"), "utf-8", True, "\r\n"),
        (b"\xff\xfe" + SAMPLE.replace("\n", "\r\n").encode("utf-16-le"), "utf-16-le", True, "\r\n"),
        (b"\xfe\xff" + SAMPLE.encode("utf-16-be"), "utf-16-be", True, "\n"),
        (SAMPLE.replace("\n", "\r\n").encode("gb18030"), "gb18030", False, "\r\n"),
        (SAMPLE.replace("\n", "\r").encode("utf-8"), "utf-8", False, "\r"),
    ],
)
def test_round_trip_preserves_bytes(tmp_path: Path, raw, encoding, bom, newline):
    path = tmp_path / "sample.txt"
    path.write_bytes(raw)

    loaded = read_text_file(path)

    assert loaded.text == SAMPLE
    assert loaded.encoding == encoding
    assert loaded.bom is bom
    assert loaded.newline == newline
    assert loaded.lossless is True

    path.write_bytes(b"")
    write_text_file(path, loaded.text, loaded)
    assert path.read_bytes() == raw


def test_edited_text_uses_original_format(tmp_path: Path):
    path = tmp_path / "a.txt"
    path.write_bytes("旧\r\n文\r\n".encode("gb18030"))
    loaded = read_text_file(path)
    assert loaded.encoding == "gb18030"

    write_text_file(path, "中\n文\n", loaded)

    assert path.read_bytes() == "中\r\n文\r\n".encode("gb18030")


def test_empty_file_defaults_to_utf8_crlf(tmp_path: Path):
    path = tmp_path / "empty.txt"
    path.write_bytes(b"")

    loaded = read_text_file(path)

    assert loaded == TextFile(text="", encoding="utf-8", bom=False, newline="\r\n", lossless=True)
    assert default_text_file() == loaded


def test_single_line_defaults_to_crlf(tmp_path: Path):
    path = tmp_path / "one.txt"
    path.write_bytes(b"only")

    assert read_text_file(path).newline == "\r\n"


def test_undecodable_bytes_are_flagged_lossy(tmp_path: Path):
    path = tmp_path / "bin.txt"
    path.write_bytes(b"ok \x80\x81\xfe\xff\xff tail")

    loaded = read_text_file(path)

    assert loaded.lossless is False
    assert "ok" in loaded.text


def test_write_refuses_lossy_format(tmp_path: Path):
    path = tmp_path / "bin.txt"
    path.write_bytes(b"\x80\x81\xfe\xff\xff")
    loaded = read_text_file(path)

    with pytest.raises(ValueError):
        write_text_file(path, "x", loaded)
    assert path.read_bytes() == b"\x80\x81\xfe\xff\xff"


def test_failed_write_keeps_original(tmp_path: Path, monkeypatch):
    path = tmp_path / "keep.txt"
    path.write_bytes(b"original")
    fmt = read_text_file(path)

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(text_io.os, "replace", boom)
    with pytest.raises(OSError):
        write_text_file(path, "changed", fmt)

    assert path.read_bytes() == b"original"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["keep.txt"]


def test_unencodable_text_raises_and_keeps_original(tmp_path: Path):
    path = tmp_path / "gbk.txt"
    path.write_bytes("中文".encode("gb18030"))
    fmt = TextFile(text="", encoding="ascii", bom=False, newline="\n", lossless=True)

    with pytest.raises(UnicodeEncodeError):
        write_text_file(path, "中文", fmt)
    assert path.read_bytes() == "中文".encode("gb18030")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["gbk.txt"]
