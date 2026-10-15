# UI Font: Faster First Paint

Date: 2026-10-15
Status: Implemented (2026-10-15) (user: "换，越快越好" — switch the UI font, as fast as possible)
Progress ledger: `docs/STATUS.md`

## 1. Goal

Remove the multi-second font fallback searches from the first window paint and
from opening the first Browser tab.

## 2. Cause (measured)

- Qt searches all ~364 installed font families when a character is missing from
  the font being used. Each search costs about 1.2–5.8 s on the GUI thread.
- The default UI font is Segoe UI, which has no Chinese glyphs, so the first
  Chinese label (welcome page, menus) triggers a search.
- The title bar close glyph `✕` (U+2715) and restore glyph `❐` (U+2750) are in
  neither Segoe UI nor Microsoft YaHei UI; `✕` alone measured 5.8 s.
- The Browser reload glyph `⟳` (U+27F3) is missing too, so the first Browser tab
  stalls the same way.
- Measured with Windows GDI `GetGlyphIndicesW` (mark missing). Qt's
  `QFontMetrics.inFontUcs4` counts fallback fonts and `QRawFont` misreads the
  YaHei font collection, so neither can be used to check coverage.

## 3. Decisions

1. Application UI font becomes **Microsoft YaHei UI** (its Latin glyphs come from
   Segoe UI), set once on the `QApplication` by `ReaderApp`, same point size.
2. Welcome page text uses exactly one family, `"Microsoft YaHei UI"`.
   The large Latin "Reader" heading uses only Segoe UI Variable Display.
   Stylesheets name exactly **one** family: each extra family in a CSS list makes
   Qt build a fallback chain on first use (measured 1.8–2.5 s each), even when the
   first family covers every glyph.
3. Title bar min/max/close buttons and Browser back/forward/reload buttons use
   **Segoe UI Symbol**, which contains every glyph they show (same glyph shapes).
4. Constants live in `reader/theme.py` (`UI_FONT_FAMILY`, `UI_FONT_STACK`,
   `SYMBOL_FONT_FAMILY`).
5. Document rendering (WebEngine CSS), code editor (Cascadia/Consolas) and hex
   view fonts are unchanged.

## 4. Testing

- `ReaderApp` sets the application font family to Microsoft YaHei UI.
- Every text shown by a new window's widgets and actions (including the maximized
  restore glyph and the Browser toolbar) exists in that widget's own primary font,
  checked with GDI glyph indices.
- Every widget resolves to exactly one font family.
- Release gate, then frozen-build cold-start measurement.

## 5. Known limit

Qt WebEngine's first initialisation calls `QFont.defaultFamily()`, which fills
Qt's fallback-font table (2–3.5 s). Segoe UI used to pay this earlier through
the Chinese fallback search, so web-rendered documents (`.md`, `.pptx`, ...) keep
about the same total time; the window just appears sooner. Native documents
defer Chromium warmup, so the cost leaves their first paint.
