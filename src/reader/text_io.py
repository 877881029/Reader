"""Lossless text file I/O: detect encoding/BOM/newline and write them back atomically."""

from __future__ import annotations

import codecs
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

_BOMS: tuple[tuple[bytes, str], ...] = (
    (codecs.BOM_UTF8, "utf-8"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
)
_BOM_FOR = {encoding: bom for bom, encoding in _BOMS}
DEFAULT_NEWLINE = "\r\n"


@dataclass(frozen=True)
class TextFile:
    text: str
    encoding: str
    bom: bool
    newline: str
    lossless: bool


def default_text_file() -> TextFile:
    return TextFile(text="", encoding="utf-8", bom=False, newline=DEFAULT_NEWLINE, lossless=True)


def _detect_newline(text: str) -> str:
    for index, char in enumerate(text):
        if char == "\n":
            return "\n"
        if char == "\r":
            return "\r\n" if text[index + 1 : index + 2] == "\n" else "\r"
    return DEFAULT_NEWLINE


def _normalise(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def decode_bytes(raw: bytes) -> TextFile:
    encoding: str | None = None
    bom = False
    text = ""
    for marker, name in _BOMS:
        if raw.startswith(marker):
            try:
                text = raw[len(marker) :].decode(name)
                encoding, bom = name, True
            except UnicodeDecodeError:
                encoding = None
            break
    if encoding is None:
        for name in ("utf-8", "gb18030"):
            try:
                text = raw.decode(name)
                encoding = name
                break
            except UnicodeDecodeError:
                continue
    if encoding is None:
        text = raw.decode("utf-8", errors="replace")
        return TextFile(_normalise(text), "utf-8", False, _detect_newline(text), False)
    return TextFile(_normalise(text), encoding, bom, _detect_newline(text), True)


def read_text_file(path: Path) -> TextFile:
    return decode_bytes(Path(path).read_bytes())


def encode_text(text: str, fmt: TextFile) -> bytes:
    if not fmt.lossless:
        raise ValueError("refusing to write a file whose encoding was not decoded losslessly")
    body = _normalise(text).replace("\n", fmt.newline).encode(fmt.encoding)
    return (_BOM_FOR.get(fmt.encoding, b"") if fmt.bom else b"") + body


def write_text_file(path: Path, text: str, fmt: TextFile) -> None:
    path = Path(path)
    data = encode_text(text, fmt)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
