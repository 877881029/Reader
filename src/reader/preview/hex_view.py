"""Fast hex viewer for binary files (memory-mapped, paints only visible rows)."""

from __future__ import annotations

import mmap
from pathlib import Path

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
