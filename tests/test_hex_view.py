from __future__ import annotations

import mmap
from pathlib import Path

import pytest

from reader.preview.hex_view import (
    ByteSource,
    format_ascii_row,
    format_hex_row,
    hex_unit_spans,
    offset_width,
)

ROW = bytes(range(16))


def test_format_hex_row_byte_word_dword():
    assert format_hex_row(ROW, 1) == " ".join(f"{b:02X}" for b in ROW)
    assert format_hex_row(ROW, 2) == "0100 0302 0504 0706 0908 0B0A 0D0C 0F0E"
    assert format_hex_row(ROW, 4) == "03020100 07060504 0B0A0908 0F0E0D0C"


def test_format_hex_row_partial_units_pad_missing_high_bytes():
    assert format_hex_row(b"\x01\x02\x03", 1) == "01 02 03"
    assert format_hex_row(b"\x01\x02\x03", 2) == "0201 --03"
    assert format_hex_row(b"\x01\x02\x03", 4) == "--030201"
    assert format_hex_row(b"", 4) == ""


def test_hex_unit_spans_match_formatting():
    for group in (1, 2, 4):
        text = format_hex_row(ROW, group)
        spans = hex_unit_spans(group)
        assert len(spans) == 16 // group
        for index, (start, width) in enumerate(spans):
            unit = ROW[index * group:(index + 1) * group]
            assert text[start:start + width] == unit[::-1].hex().upper()


def test_format_ascii_row_maps_printable_only():
    assert format_ascii_row(b"Hi!\x00\x7f\x20~\xff") == "Hi!.. ~."


@pytest.mark.parametrize(
    ("size", "width"),
    [(0, 8), (16, 8), (2**32, 8), (2**32 + 1, 9), (2**40, 10)],
)
def test_offset_width(size: int, width: int):
    assert offset_width(size) == width


def test_byte_source_maps_and_reads(tmp_path: Path):
    path = tmp_path / "a.bin"
    path.write_bytes(bytes(range(256)) * 4)
    source = ByteSource(path)
    try:
        assert source.size == 1024
        assert source.mapped is True
        assert source.read(16, 16) == bytes(range(16, 32))
        assert source.read(1020, 16) == bytes(range(252, 256))
        assert source.read(5000, 16) == b""
    finally:
        source.close()
    path.unlink()


def test_byte_source_empty_file(tmp_path: Path):
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")
    source = ByteSource(path)
    assert source.size == 0
    assert source.read(0, 16) == b""
    source.close()


def test_byte_source_falls_back_when_mmap_fails(tmp_path: Path, monkeypatch):
    path = tmp_path / "a.bin"
    path.write_bytes(b"abcdefghijklmnopqrstuvwxyz")

    def boom(*_args, **_kwargs):
        raise OSError("no map")

    monkeypatch.setattr(mmap, "mmap", boom)
    source = ByteSource(path)
    try:
        assert source.mapped is False
        assert source.read(2, 4) == b"cdef"
    finally:
        source.close()
    path.unlink()
