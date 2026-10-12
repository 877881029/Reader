"""Fast hex viewer for binary files (memory-mapped, paints only visible rows)."""

from __future__ import annotations

import math
import mmap
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from reader.theme import CARD, HOVER, INK, LINE, MUTED, PAPER

BYTES_PER_ROW = 16
GROUP_SIZES = (1, 2, 4)
_ASCII_TABLE = "".join(chr(code) if 0x20 <= code <= 0x7E else "." for code in range(256))


def format_hex_row(data: bytes, group: int) -> str:
    """Hex for one row; Word/DWord units are little-endian values, missing bytes ``--``."""
    units: list[str] = []
    for start in range(0, len(data), group):
        chunk = data[start:start + group]
        digits = chunk[::-1].hex().upper()
        units.append("--" * (group - len(chunk)) + digits)
    return " ".join(units)


MARGIN = 12
OFFSET_GAP = 3
HALF_GAP = 1
ASCII_GAP = 3
DEFAULT_PIXEL_SIZE = 14


def hex_unit_layout(group: int) -> list[tuple[int, int]]:
    """Display (start column, width) of each unit, with an extra gap after byte 7."""
    width = 2 * group
    return [
        (index * (width + 1) + (HALF_GAP if index * group >= BYTES_PER_ROW // 2 else 0), width)
        for index in range(BYTES_PER_ROW // group)
    ]


def hex_unit_spans(group: int) -> list[tuple[int, int]]:
    """(start column, width) of each unit inside a formatted full row."""
    width = 2 * group
    return [(index * (width + 1), width) for index in range(BYTES_PER_ROW // group)]


def format_ascii_row(data: bytes) -> str:
    return "".join(_ASCII_TABLE[byte] for byte in data)


def offset_width(size: int) -> int:
    return max(8, len(f"{max(size - 1, 0):X}"))


class ByteSource:
    """Read-only random access to a file; memory-mapped when possible."""

    def __init__(self, path: Path) -> None:
        self._file = open(path, "rb")  # noqa: SIM115 - closed in close()
        self._file.seek(0, 2)
        self.size = self._file.tell()
        self._map: mmap.mmap | None = None
        if self.size > 0:
            try:
                self._map = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
            except (OSError, ValueError):
                self._map = None

    @property
    def mapped(self) -> bool:
        return self._map is not None

    def read(self, offset: int, length: int) -> bytes:
        if offset >= self.size or length <= 0 or self._file.closed:
            return b""
        end = min(offset + length, self.size)
        if self._map is not None:
            return self._map[offset:end]
        self._file.seek(offset)
        return self._file.read(end - offset)

    def close(self) -> None:
        if self._map is not None:
            self._map.close()
            self._map = None
        if not self._file.closed:
            self._file.close()


class _HexArea(QAbstractScrollArea):
    """Paints only the rows currently in view."""

    def __init__(self, owner: HexView) -> None:
        super().__init__(owner)
        self.setObjectName("hexArea")
        self._owner = owner
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.viewport().setMouseTracking(True)
        self.viewport().setAutoFillBackground(False)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self._owner._update_scrollbars()

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt API
        self._owner._paint(self.viewport())

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._owner._hover(event.position().toPoint())
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._owner._hover(None)
        super().leaveEvent(event)


class HexView(QWidget):
    """Offset | 16 bytes as Byte/Word/DWord units | ASCII, with linked hover."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("hexView")
        self._source: ByteSource | None = None
        self._path: Path | None = None
        self._group = 1
        self._highlight: tuple[int, int] | None = None

        toolbar = QWidget(self)
        toolbar.setObjectName("hexToolbar")
        toolbar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        toolbar.setFixedHeight(40)
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(12, 4, 12, 4)
        row.setSpacing(4)
        self._group_buttons: dict[int, QToolButton] = {}
        group_box = QButtonGroup(toolbar)
        group_box.setExclusive(True)
        for size, name, text in ((1, "hexGroupByte", "Byte"), (2, "hexGroupWord", "Word"), (4, "hexGroupDWord", "DWord")):
            button = QToolButton(toolbar)
            button.setObjectName(name)
            button.setText(text)
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.clicked.connect(lambda _checked=False, s=size: self.set_group(s))
            group_box.addButton(button)
            row.addWidget(button)
            self._group_buttons[size] = button
        self._group_buttons[1].setChecked(True)
        self._info = QLabel("", toolbar)
        self._info.setObjectName("hexInfo")
        self._size = QLabel("", toolbar)
        self._size.setObjectName("hexSize")
        row.addSpacing(12)
        row.addWidget(self._info, 1)
        row.addWidget(self._size)

        self._area = _HexArea(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(toolbar)
        layout.addWidget(self._area, 1)

        self._left = float(MARGIN)
        self._apply_pixel_size(DEFAULT_PIXEL_SIZE)

        self.setStyleSheet(
            f"""
            QWidget#hexToolbar {{
                background: {PAPER};
                border-bottom: 1px solid {LINE};
            }}
            QToolButton#hexGroupByte, QToolButton#hexGroupWord, QToolButton#hexGroupDWord {{
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px 10px;
                color: {MUTED};
            }}
            QToolButton#hexGroupByte:checked, QToolButton#hexGroupWord:checked,
            QToolButton#hexGroupDWord:checked {{
                background: {HOVER};
                color: {INK};
            }}
            QLabel#hexInfo, QLabel#hexSize {{ color: {MUTED}; }}
            """
        )

    # -- public API -----------------------------------------------------------------

    def area(self) -> QAbstractScrollArea:
        return self._area

    def path(self) -> Path | None:
        return self._path

    def load_path(self, path: Path) -> None:
        self.shutdown()
        self._path = Path(path)
        self._source = ByteSource(self._path)
        size = self._source.size
        if size == 0:
            self._size.setText("空文件")
        elif size < 1024:
            self._size.setText(f"{size:,} 字节")
        else:
            self._size.setText(f"{_human_size(size)}（{size:,} 字节）")
        self._highlight = None
        self._info.clear()
        self._area.verticalScrollBar().setValue(0)
        self._update_scrollbars()
        self._area.viewport().update()

    def shutdown(self) -> None:
        if self._source is not None:
            self._source.close()
            self._source = None

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        self.shutdown()
        super().closeEvent(event)

    def size_bytes(self) -> int:
        return self._source.size if self._source is not None else 0

    def row_count(self) -> int:
        return (self.size_bytes() + BYTES_PER_ROW - 1) // BYTES_PER_ROW

    def group(self) -> int:
        return self._group

    def set_group(self, group: int) -> None:
        if group not in GROUP_SIZES:
            return
        self._group = group
        self._group_buttons[group].setChecked(True)
        self._highlight = None
        self._info.clear()
        self._update_scrollbars()
        self._area.viewport().update()

    def highlighted(self) -> tuple[int, int] | None:
        return self._highlight

    def row_text(self, row: int) -> tuple[str, str, str]:
        data = self._row_bytes(row)
        width = offset_width(self.size_bytes())
        return (
            f"{row * BYTES_PER_ROW:0{width}X}",
            format_hex_row(data, self._group),
            format_ascii_row(data),
        )

    def cell_center(self, offset: int, column: str) -> QPoint:
        row = offset // BYTES_PER_ROW
        within = offset % BYTES_PER_ROW
        y = self._header_height() + (row - self._first_row()) * self._row_height + self._row_height / 2
        if column == "ascii":
            x = self._ascii_x() + (within + 0.5) * self._char_width
        else:
            start, width = hex_unit_layout(self._group)[within // self._group]
            x = self._hex_x() + (start + width / 2) * self._char_width
        return QPoint(round(x - self._area.horizontalScrollBar().value()), round(y))

    def highlight_rects(self) -> list[QRectF]:
        """Viewport rectangles (hex, ascii) of the highlighted unit, if visible."""
        if self._highlight is None:
            return []
        offset, length = self._highlight
        row = offset // BYTES_PER_ROW
        within = offset % BYTES_PER_ROW
        top = self._header_height() + (row - self._first_row()) * self._row_height
        dx = -self._area.horizontalScrollBar().value()
        cw = self._char_width
        start, width = hex_unit_layout(self._group)[within // self._group]
        return [
            QRectF(self._hex_x() + dx + (start - 0.35) * cw, top, (width + 0.7) * cw, self._row_height),
            QRectF(self._ascii_x() + dx + within * cw, top, length * cw, self._row_height),
        ]

    def unit_at(self, point: QPoint) -> tuple[int, int] | None:
        size = self.size_bytes()
        y = point.y() - self._header_height()
        if y < 0 or size == 0:
            return None
        row = self._first_row() + int(y // self._row_height)
        if row >= self.row_count():
            return None
        x = point.x() + self._area.horizontalScrollBar().value()
        cw = self._char_width
        byte: int | None = None
        layout = hex_unit_layout(self._group)
        column = (x - self._hex_x()) / cw
        first_start = layout[0][0]
        last_start, last_width = layout[-1]
        if first_start - 1.0 <= column < last_start + last_width + 1.0:
            # Nearest unit centre: gaps belong to the closest unit.
            index = min(
                range(len(layout)),
                key=lambda i: abs(column - (layout[i][0] + layout[i][1] / 2)),
            )
            byte = index * self._group
        else:
            ascii_column = (x - self._ascii_x()) / cw
            if 0 <= ascii_column < BYTES_PER_ROW:
                byte = int(ascii_column)
        if byte is None:
            return None
        offset = row * BYTES_PER_ROW + byte
        offset -= offset % self._group
        if offset >= size:
            return None
        return offset, min(self._group, size - offset)

    # -- layout ---------------------------------------------------------------------

    def _apply_pixel_size(self, pixel_size: int) -> None:
        font = QFont("Cascadia Mono")
        font.setFamilies(["Cascadia Mono", "Consolas", "Courier New"])
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPixelSize(int(pixel_size))
        self._pixel_size = int(pixel_size)
        self._area.setFont(font)
        metrics = QFontMetricsF(font)
        self._char_width = max(metrics.horizontalAdvance("0"), 1.0)
        self._row_height = int(math.ceil(metrics.height())) + 6
        self._ascent = metrics.ascent() + 3

    def pixel_size(self) -> int:
        return self._pixel_size

    def _header_height(self) -> int:
        return self._row_height + 6

    def _offset_x(self) -> float:
        return self._left

    def _hex_x(self) -> float:
        return self._offset_x() + (offset_width(self.size_bytes()) + OFFSET_GAP) * self._char_width

    def _hex_chars(self) -> int:
        start, width = hex_unit_layout(self._group)[-1]
        return start + width

    def _ascii_x(self) -> float:
        return self._hex_x() + (self._hex_chars() + ASCII_GAP) * self._char_width

    def _content_width(self) -> int:
        return int(math.ceil(self._ascii_x() + BYTES_PER_ROW * self._char_width + MARGIN))

    def _visible_rows(self) -> int:
        usable = self._area.viewport().height() - self._header_height()
        return max(1, usable // self._row_height)

    def _first_row(self) -> int:
        return self._area.verticalScrollBar().value()

    def _update_scrollbars(self) -> None:
        visible = self._visible_rows()
        vertical = self._area.verticalScrollBar()
        vertical.setRange(0, max(0, self.row_count() - visible))
        vertical.setPageStep(visible)
        vertical.setSingleStep(1)
        horizontal = self._area.horizontalScrollBar()
        width = self._area.viewport().width()
        horizontal.setRange(0, max(0, self._content_width() - width))
        horizontal.setPageStep(width)
        horizontal.setSingleStep(max(1, int(self._char_width)))

    def _row_bytes(self, row: int) -> bytes:
        if self._source is None:
            return b""
        return self._source.read(row * BYTES_PER_ROW, BYTES_PER_ROW)

    # -- interaction ----------------------------------------------------------------

    def _hover(self, point: QPoint | None) -> None:
        unit = self.unit_at(point) if point is not None else None
        if unit == self._highlight:
            return
        self._highlight = unit
        if unit is None:
            self._info.clear()
        else:
            offset, length = unit
            data = self._source.read(offset, length) if self._source else b""
            value = int.from_bytes(data, "little")
            self._info.setText(
                f"偏移 0x{offset:0{offset_width(self.size_bytes())}X}"
                f"    值 0x{value:0{2 * length}X}（{value}）"
            )
        self._area.viewport().update()

    # -- painting -------------------------------------------------------------------

    def _paint(self, viewport: QWidget) -> None:
        painter = QPainter(viewport)
        painter.fillRect(viewport.rect(), QColor(CARD))
        painter.setFont(self._area.font())
        dx = -self._area.horizontalScrollBar().value()
        cw = self._char_width
        header = self._header_height()
        if self.size_bytes() == 0:
            painter.setPen(QColor(MUTED))
            painter.drawText(QPointF(self._offset_x() + dx, self._ascent + 6), "空文件")
            painter.end()
            return

        layout = hex_unit_layout(self._group)
        hex_x = self._hex_x() + dx
        ascii_x = self._ascii_x() + dx
        # Every cell is drawn at its own float position so glyphs, hit testing
        # and highlights share one geometry and never drift across the row.
        painter.setPen(QColor(MUTED))
        header_baseline = self._ascent
        for index, (start, width) in enumerate(layout):
            label = f"{index * self._group:02X}"
            painter.drawText(QPointF(hex_x + (start + width - len(label)) * cw, header_baseline), label)
        for index in range(BYTES_PER_ROW):
            painter.drawText(QPointF(ascii_x + index * cw, header_baseline), f"{index:X}")
        painter.setPen(QColor(LINE))
        painter.drawLine(0, header - 3, viewport.width(), header - 3)

        first = self._first_row()
        last = min(self.row_count(), first + self._visible_rows() + 1)
        highlight = QColor(_HIGHLIGHT)
        rects = self.highlight_rects()
        highlight_row = self._highlight[0] // BYTES_PER_ROW if self._highlight else -1
        offset_digits = offset_width(self.size_bytes())
        for row in range(first, last):
            top = header + (row - first) * self._row_height
            if row == highlight_row:
                for rect in rects:
                    painter.fillRect(rect, highlight)
            data = self._row_bytes(row)
            baseline = top + self._ascent
            painter.setPen(QColor(MUTED))
            painter.drawText(QPointF(self._offset_x() + dx, baseline), f"{row * BYTES_PER_ROW:0{offset_digits}X}")
            painter.setPen(QColor(INK))
            for index, (start, _width) in enumerate(layout):
                chunk = data[index * self._group:(index + 1) * self._group]
                if not chunk:
                    break
                painter.drawText(QPointF(hex_x + start * cw, baseline), format_hex_row(chunk, self._group))
            for index, char in enumerate(format_ascii_row(data)):
                painter.drawText(QPointF(ascii_x + index * cw, baseline), char)
        separator = ascii_x - 1.5 * cw
        painter.setPen(QColor(LINE))
        painter.drawLine(QPointF(separator, header), QPointF(separator, viewport.height()))
        painter.end()


_HIGHLIGHT = "#f2dfb4"


def _human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"
