# Hex View Alignment and Adaptive Layout Design

Status: Implemented
Progress ledger: `docs/STATUS.md`

## Background

1. The hover highlight does not sit on the byte under the mouse. Cause: column
   positions use `QFontMetrics.horizontalAdvance("0")` (rounded int) while each
   row is drawn as one string with fractional advances, so error accumulates
   across the row.
2. Rows use a fixed 10pt font and leave a large empty area on the right.

## Scope

- Exact geometry: char width from `QFontMetricsF`; every offset, hex unit and
  ASCII character is drawn at its own computed float position, and hit testing
  uses the same geometry. A unit's hover area includes half of the surrounding
  gaps (no dead zones between units).
- Layout: offset | 3-char gap | hex units separated by 1 char with an extra
  1-char gap between byte 7 and byte 8 | 3-char gap + rule | ASCII.
- Adaptive font: pixel size chosen so the layout fills the viewport width,
  clamped to 13–22 px; when capped, the block is centred horizontally; when
  the minimum still overflows, horizontal scrolling remains.
- Manual zoom: `Ctrl+wheel`, `Ctrl+=`/`Ctrl++`, `Ctrl+-` step the pixel size
  (10–32 px) and leave auto mode; `Ctrl+0` returns to auto.
- Text formatting helpers (`format_hex_row`, `row_text`) are unchanged.

## Acceptance

- For every byte and grouping, the highlight rectangle covers the glyphs of
  that unit with clean edges (rendered-pixel test) and `unit_at(cell_center)`
  round-trips.
- Wider viewports get larger fonts up to the cap, then centring; narrow ones
  scroll horizontally.
- Zoom shortcuts change size within bounds; Ctrl+0 restores auto fit.