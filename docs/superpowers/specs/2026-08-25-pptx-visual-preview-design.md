# PPTX Visual Preview Design

Date: 2026-08-25  
Status: Approved by user; awaiting implementation plan  
Depends on: `docs/superpowers/specs/2026-08-24-reader-ux-packaging-design.md`  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Replace the current PPTX builtin preview (text/table extraction redrawn as HTML) with a **local visual slide viewer** comparable to Cursor’s PPTX Viewer plugin:

1. Each slide is rendered as a real canvas (background, images, text, shapes, tables, basic charts), not a “Slide N + paragraphs” outline.
2. Default open path stays **fast and offline**: no PowerPoint COM, no network.
3. UI matches the approved layout: **thumbnail rail on the left**, **one slide on the right**, plus prev/next, page number, zoom, and fit-to-window.
4. “Office 高保真” remains optional for machines that have PowerPoint.

This increment does not add dual pane, translation, format conversion, or animation playback.

## 2. Problem (current)

`src/reader/formats/pptx.py` uses `python-pptx` to extract shape text and tables into HTML sections. Layout, theme, pictures, and fonts are discarded. That is why daily decks look like figure 1 (outline) instead of figure 2 (slide canvas).

## 3. Non-goals

- Do not copy or vendor `astx-jp.vscode-pptx-viewer` (proprietary, no derivative works).
- Do not require PowerPoint, LibreOffice, or internet for the default preview.
- Do not play animations, video, or macros in v1.
- Do not change Word/Excel/Markdown builtin pipelines except shared viewer plumbing if required.
- Do not auto-switch PPTX to Office-first.

## 4. Approved decisions

| Topic | Choice |
|---|---|
| Renderer | Local Web/PPTX renderer inside `QWebEngineView` |
| PowerPoint dependency | None for default preview |
| Layout | Left thumbnails + right single slide + zoom/nav (Cursor-like) |
| v1 fidelity | Static high-fidelity: masters/themes, pictures, text styles, common shapes, tables, basic charts |
| Fallback | Keep current text extractor as “文本模式”; Office 高保真 stays as optional COM PDF/HTML |

## 5. Architecture

- New bundled web assets (HTML/JS/CSS + license-compatible renderer, pinned version) loaded by `QWebEngineView`.
- Builtin PPTX preview returns a viewer page that reads the file locally (file URL or injected bytes) and paints SVG/Canvas slides.
- Pipeline default for `.pptx` becomes this visual viewer. `python-pptx` HTML remains a fallback when the visual viewer cannot parse the file.
- Worker/cache keys must distinguish `visual` vs `text` vs `office` so caches do not mix.
- No COM probe on first open. GUI stays non-blocking (`正在加载…` then first slide).
- PyInstaller onedir must collect the web assets; frozen `resource_path` must resolve them.

## 6. UI

- Left: scaled thumbnails for all slides; current slide highlighted; click to jump.
- Right: one slide, original aspect ratio, letterboxed if needed.
- Controls: previous, next, page index, zoom out/in, fit window.
- Keys: Left/Right, PageUp/PageDown, Home/End.
- Missing fonts: substitute and continue; do not fail the whole deck.
- One slide parse error: placeholder on that slide only.

## 7. Error handling

- Encrypted/corrupt PPTX: clear error; offer 文本模式 if extraction still works.
- Visual renderer load failure: fall back to text HTML and status `内置预览（视觉渲染失败）`.
- Office 高保真 failure: unchanged (keep last builtin visual or text result).

## 8. Testing (TDD)

- Fixture decks with picture, themed background, table, and a simple chart.
- Default `.pptx` open does not call `office.available_for` / `export`.
- Viewer reports slide count matching the fixture; first slide is selected.
- Thumbnail click and keyboard navigation change the current slide.
- Raster content is present (not text-only outline).
- No outbound network from the viewer page.
- Frozen/resource path loads viewer assets from the bundled location.

## 9. Process requirement

Implementation must follow `docs/STATUS.md` and `.cursor/rules/git-progress-handoff.mdc`: commit goals and progress to git at each design/plan/task boundary so a new AI session can resume without chat history.

## 10. Compatibility amendment: exact OOXML relationship matching

Date: 2026-08-26  
Status: Approved by user (Approach A)

Real-world deck `canis_handover.pptx` exposed a parser defect in pinned
`pptx-viewer@0.2.2`: relationship lookup stores terminal type names such as
`slide`, `slideMaster`, and `slideLayout`, but fallback lookup uses substring
matching. When slide relationships precede the master relationship,
`getByType("relationships/slideMaster")` incorrectly returns slides. The parser
then treats slide XML as masters, leaves `slideLayouts` empty, and drops
placeholder-only title/body shapes because their bounds live in the layout.
The UI remains responsive but the rendered slide is blank.

Approved fix:

- Keep `pptx-viewer@0.2.2` pinned and apply a deterministic local MIT-compatible
  patch after `npm ci`.
- Relationship type lookup must compare the exact terminal type name; `slide`
  must never match `slideMaster` or `slideLayout`.
- The patch command must fail fast if the pinned package no longer contains the
  expected source, so an upstream upgrade cannot silently omit the fix.
- The committed fixture must order slide relationships before slide-master
  relationships, reproducing the real deck without committing internal user
  content.
- Tests must assert one parsed master, non-empty layouts, inherited title/body
  placeholders, and visible text in both Node/jsdom and real QWebEngine.
- Rebuild the committed bundle and frozen Reader, rerun full regression and
  frozen smoke, refresh the desktop shortcut, and record hashes in STATUS.
