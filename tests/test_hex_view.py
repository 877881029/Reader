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


# --- HexView widget -------------------------------------------------------------


from PySide6.QtCore import QEvent, QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QToolButton  # noqa: E402

from reader.preview.hex_view import HexView  # noqa: E402


def _hover(view: HexView, point: QPoint) -> None:
    viewport = view.area().viewport()
    event = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(point),
        QPointF(viewport.mapToGlobal(point)),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(viewport, event)


@pytest.fixture
def hex_view(qtbot, tmp_path: Path):
    path = tmp_path / "data.bin"
    path.write_bytes(bytes(range(256)) + b"Hello, Reader!")
    view = HexView()
    qtbot.addWidget(view)
    view.resize(1000, 500)
    view.load_path(path)
    view.show()
    qtbot.waitExposed(view)
    yield view, path
    view.shutdown()


def test_hex_view_rows_toolbar_and_size(hex_view):
    view, _path = hex_view
    assert view.objectName() == "hexView"
    assert view.row_count() == 17
    assert view.row_text(16) == ("00000100", "48 65 6C 6C 6F 2C 20 52 65 61 64 65 72 21", "Hello, Reader!")
    assert "270 字节" in view.findChild(QLabel, "hexSize").text()
    buttons = [view.findChild(QToolButton, n) for n in ("hexGroupByte", "hexGroupWord", "hexGroupDWord")]
    assert [b.text() for b in buttons] == ["Byte", "Word", "DWord"]
    assert buttons[0].isChecked()


def test_hex_view_group_switch_reformats(hex_view):
    view, _path = hex_view
    view.findChild(QToolButton, "hexGroupDWord").click()
    assert view.group() == 4
    assert view.row_text(0)[1] == "03020100 07060504 0B0A0908 0F0E0D0C"
    view.findChild(QToolButton, "hexGroupWord").click()
    assert view.row_text(16)[1] == "6548 6C6C 2C6F 5220 6165 6564 2172"


def test_hex_and_ascii_hover_highlight_same_unit(hex_view):
    view, _path = hex_view
    view.set_group(4)

    _hover(view, view.cell_center(0x25, "hex"))
    assert view.highlighted() == (0x24, 4)
    assert "0x00000024" in view.findChild(QLabel, "hexInfo").text()
    assert "0x27262524" in view.findChild(QLabel, "hexInfo").text()

    _hover(view, view.cell_center(0x26, "ascii"))
    assert view.highlighted() == (0x24, 4)

    view.set_group(1)
    _hover(view, view.cell_center(0x26, "ascii"))
    assert view.highlighted() == (0x26, 1)

    _hover(view, QPoint(2, 2))
    assert view.highlighted() is None


def test_hover_on_partial_last_unit_is_clamped(hex_view):
    view, _path = hex_view
    view.set_group(4)
    _hover(view, view.cell_center(268, "hex"))
    assert view.highlighted() == (268, 2)


def _make_sparse(handle) -> None:
    # Avoid NTFS zero-filling 1 GiB just to create the fixture.
    import ctypes
    import msvcrt
    import os

    if os.name != "nt":
        return
    from ctypes import wintypes

    returned = wintypes.DWORD()
    ctypes.windll.kernel32.DeviceIoControl(
        wintypes.HANDLE(msvcrt.get_osfhandle(handle.fileno())),
        0x000900C4,  # FSCTL_SET_SPARSE
        None, 0, None, 0, ctypes.byref(returned), None,
    )


def test_large_sparse_file_opens_fast_and_scrolls_to_end(qtbot, tmp_path: Path):
    import time

    path = tmp_path / "big.bin"
    with open(path, "wb") as handle:
        _make_sparse(handle)
        handle.seek(2**30 - 1)
        handle.write(b"\x00")
    view = HexView()
    qtbot.addWidget(view)
    view.resize(900, 500)
    started = time.perf_counter()
    view.load_path(path)
    view.show()
    qtbot.waitExposed(view)
    view.grab()
    elapsed = time.perf_counter() - started
    try:
        assert elapsed < 1.5
        assert view.row_count() == 2**26
        bar = view.area().verticalScrollBar()
        bar.setValue(bar.maximum())
        view.grab()
        assert view.row_text(2**26 - 1) == ("3FFFFFF0", " ".join(["00"] * 16), "." * 16)
    finally:
        view.shutdown()


def test_empty_file_and_shutdown_release_handle(qtbot, tmp_path: Path):
    empty = tmp_path / "e.bin"
    empty.write_bytes(b"")
    view = HexView()
    qtbot.addWidget(view)
    view.load_path(empty)
    assert view.row_count() == 0
    assert "空文件" in view.findChild(QLabel, "hexSize").text()
    view.grab()
    view.shutdown()
    empty.unlink()

    data = tmp_path / "d.bin"
    data.write_bytes(b"x" * 64)
    other = HexView()
    qtbot.addWidget(other)
    other.load_path(data)
    other.shutdown()
    data.unlink()
    assert not data.exists()


# --- exact geometry ---------------------------------------------------------------


def _ink_columns(image, rect, dpr: float) -> list[int]:
    """Device x-columns inside ``rect`` (logical) that contain dark glyph pixels."""
    top = int(rect.top() * dpr) + 2
    bottom = int(rect.bottom() * dpr) - 2
    columns = []
    for x in range(int(rect.left() * dpr), int(rect.right() * dpr) + 1):
        for y in range(top, bottom):
            if 0 <= x < image.width() and 0 <= y < image.height() and image.pixelColor(x, y).lightness() < 110:
                columns.append(x)
                break
    return columns


@pytest.mark.parametrize("group", [1, 2, 4])
def test_highlight_covers_hovered_glyphs_with_clean_edges(qtbot, tmp_path: Path, group: int):
    path = tmp_path / "ink.bin"
    path.write_bytes(b"\x88" * 64)
    view = HexView()
    qtbot.addWidget(view)
    view.resize(1400, 400)
    view.load_path(path)
    view.show()
    qtbot.waitExposed(view)
    view.set_group(group)
    try:
        for offset in range(0, 16, group):
            _hover(view, view.cell_center(offset, "hex"))
            assert view.highlighted() == (offset, group)
            hex_rect, ascii_rect = view.highlight_rects()
            image = view.area().viewport().grab().toImage()
            dpr = image.devicePixelRatio()
            ink = _ink_columns(image, hex_rect, dpr)
            assert ink, f"no glyph ink inside highlight for offset {offset}"
            left = int(hex_rect.left() * dpr)
            right = int(hex_rect.right() * dpr)
            assert min(ink) > left + 1 and max(ink) < right - 1, (offset, left, right, min(ink), max(ink))
            ascii_ink = _ink_columns(image, ascii_rect, dpr)
            assert ascii_ink
    finally:
        view.shutdown()


def test_hover_in_gap_selects_nearest_unit(hex_view):
    view, _path = hex_view
    view.set_group(1)
    first = view.cell_center(0, "hex")
    second = view.cell_center(1, "hex")
    near_first = QPoint(first.x() + int((second.x() - first.x()) * 0.4), first.y())
    near_second = QPoint(first.x() + int((second.x() - first.x()) * 0.6), first.y())
    _hover(view, near_first)
    assert view.highlighted() == (0, 1)
    _hover(view, near_second)
    assert view.highlighted() == (1, 1)


def test_cell_centres_round_trip_with_half_gap(hex_view):
    view, _path = hex_view
    for group in (1, 2, 4):
        view.set_group(group)
        for offset in range(0, 32, group):
            _hover(view, view.cell_center(offset, "hex"))
            assert view.highlighted() == (offset, group)
            _hover(view, view.cell_center(offset, "ascii"))
            assert view.highlighted() == (offset, group)
    view.set_group(1)
    gap_7_8 = view.cell_center(8, "hex").x() - view.cell_center(7, "hex").x()
    gap_6_7 = view.cell_center(7, "hex").x() - view.cell_center(6, "hex").x()
    assert gap_7_8 > gap_6_7
