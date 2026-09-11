# SVG Reading Design

Date: 2026-09-11  
Status: Implemented (QtSvg paper fit-to-pane graphic tabs)  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Reader opens `.svg` as a first-class **visual** document tab: the graphic is drawn on the paper canvas, fitted to the pane, read-only. Double-click / Open With / drag / `Ctrl+O` all work.

This is a picture viewer for SVG, not an XML code page.

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.

## 2. Decisions

| Topic | Choice |
|---|---|
| Scope | `.svg` only (not `.png` / `.jpg` / `.webp` / `.html`) |
| Renderer | `PySide6.QtSvg.QSvgRenderer` (no Chromium, no SVG scripts) |
| Layout | Paper background; graphic kept aspect-ratio, letterboxed, padded |
| Interaction | Read-only; no edit; **Ctrl+wheel zoom** (no on-screen zoom chrome); drag to pan when zoomed |
| Invalid file | Still open a tab; show centered `无法渲染此 SVG` |
| Cache | Skip preview cache (source file is already local) |
| Find | `Ctrl+F` searches the UTF-8 source text (substring, no highlight) |
| Defaults | `.svg` joins `associate.EXTENSIONS`; Settings claim stays `.pdf` only |

Office COM is never called. `mode="visual"` / `"text"` / `"office"` all return the same builtin SVG result.

## 3. Surfaces

- `sniff.SUPPORTED_EXTENSIONS` and `associate.EXTENSIONS`
- `reader.formats.svg.to_preview` → `PreviewResult(kind="svg", svg_path=resolved, html="", status_label="内置预览")`
- `_default_viewer` builds `SvgView`
- Open dialog filter; welcome recent badge `SVG`
- README + `docs/Reader功能全解.md`
- Frozen `reader.spec` collects `PySide6.QtSvg`

## 4. Non-goals

- Raster images (see `2026-09-11-graphic-zoom-images-design.md`)
- SMIL / JavaScript animation
- Inkscape-level editing
- Changing PDF pin / hit-test / WebEngine warmup

## 5. Testing

- sniff / `decide_open` / pipeline / associate / open dialog accept `.svg`
- `to_preview` points at the source; `asset_dir` is None; Office is not called
- `SvgView` reports valid for a circle SVG, invalid for garbage, uses paper fill
- `_default_viewer` returns `SvgView`
- Cache `put(kind="svg")` raises
- Caption hit tests stay green
- Frozen smoke still passes; README lists `.svg`
