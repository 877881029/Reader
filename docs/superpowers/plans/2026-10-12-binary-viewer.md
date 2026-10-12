# Binary (Hex) Viewer Implementation Plan

Status: Implemented

**Spec:** `docs/superpowers/specs/2026-10-12-binary-viewer-design.md`

## Task 1: Format helpers and byte source

**RED** `tests/test_hex_view.py`: `format_hex_row` for byte/word/dword and
partial units; `format_ascii_row`; `ByteSource` mmap/empty/fallback; offset width.
**GREEN** `src/reader/preview/hex_view.py` helpers.

## Task 2: HexView widget

**RED** row count, group switch, `unit_at` for hex/ascii positions, linked
highlight, toolbar info, 1 GiB sparse file speed, shutdown releases file.
**GREEN** `HexView`.

## Task 3: Pipeline and window integration

**RED** sniff/associate/open-dialog include `.bin`; `preview()` returns
`kind="binary"`; worker skips cache; `_default_viewer` builds `HexView`.
**GREEN** `formats/binary.py`, result kind/field, wiring.

## Task 4: Docs, release gate, install

README, 功能全解, STATUS; `verify.ps1 -Release`; `install_local.ps1`.