# Binary (Hex) Viewer Design

Status: Implemented
Progress ledger: `docs/STATUS.md`

## Background

The user wants Reader to open `.bin` files quickly as a hex view: 16 bytes per
row, switchable Byte / Word / DWord grouping, an ASCII column on the right,
and linked hover highlighting between a hex unit and its ASCII characters.
Large files must appear immediately.

## Scope

- `.bin` becomes a supported extension (sniff, open dialog, drag/drop,
  file associations like every other format). `formats/binary.py::to_preview`
  returns `PreviewResult(kind="binary", binary_path=…)` without reading the file;
  the preview worker never caches it.
- `HexView` (`QAbstractScrollArea`, object name `hexView`):
  - Data source: read-only `mmap` (instant for any size); falls back to seek/read
    when mapping fails; empty files show `空文件`. `shutdown()` releases the map
    so the file is not kept locked.
  - Only visible rows are formatted and painted; scroll range is in rows.
  - Columns: offset (8 hex digits, wider above 4 GiB) | 16 bytes as units | ASCII
    (0x20–0x7E shown, others `.`).
  - Grouping toolbar `Byte | Word | DWord` (`hexGroupByte/Word/DWord`).
    Word/DWord units show the little-endian value (`b1b0`, `b3b2b1b0`); a partial
    last unit pads missing high bytes with `--`.
  - Hovering a hex unit or an ASCII character highlights the whole unit in both
    columns; the toolbar shows offset and the unit value in hex and decimal.
  - Header shows the file size; keyboard/wheel scrolling via the scroll area.

## Non-goals

- Editing, search inside binary, big-endian toggle, Ctrl+G offset jump (later).

## Acceptance

- Formatting functions produce the exact strings for each grouping, including
  partial units.
- A 1 GiB sparse file opens without reading it (row count correct, fast).
- Hover on hex and on ASCII yields the same highlighted unit range.
- After `shutdown()` the file can be deleted.
- Real window: opening `.bin` shows the hex view.