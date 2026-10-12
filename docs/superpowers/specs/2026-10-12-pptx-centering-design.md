# PPTX Slide Centering and Scrollbar-Free Stage Design

Status: Approved
Progress ledger: `docs/STATUS.md`

## Background

Opening a PPTX shows the slide shifted right/down and partly cut off, with
vertical and horizontal scrollbars; the user has to adjust it every time.
Root cause: the slide host keeps its native size (e.g. 1280x720) in layout and
is only visually shrunk with `transform: scale()` around its centre. The grid
cell and `overflow: auto` work on the unscaled box, so the slide is offset and
scrollbars appear. Fit also ignored the stage's 16px padding.

## Scope

- Stage becomes `overflow: hidden` (no scrollbars) and `position: relative`.
- A canvas wrapper (`.viewer-shell__canvas`) is absolutely positioned at
  `left = (stageW - slideW*zoom)/2 + panX`, `top = (stageH - slideH*zoom)/2 + panY`
  and sized to the scaled slide; the host scales from the top-left corner.
  The slide is therefore centred at any zoom.
- Fit = `fitScale(stageW - 2*16, stageH - 2*16, …)` (16px gutter); default on
  open and on resize while in fit mode.
- Zoom kept: toolbar `-` / `+` / 适合窗口, plus shortcuts `Ctrl+=`/`Ctrl++`
  (in), `Ctrl+-` (out), `Ctrl+0` (fit) and `Ctrl+wheel`. All prevent default so
  Chromium never page-zooms.
- When the zoomed slide is larger than the stage it can be panned by dragging
  with the mouse or with the plain wheel (Shift+wheel horizontal). Pan is
  clamped so the slide edge never leaves the stage gutter; it resets on fit and
  is 0 on any axis where the slide fits.

## Non-goals

- Thumbnail rail scrolling (it keeps its list scroll), slide transitions.

## Acceptance

- After open, canvas is centred: equal left/right and top/bottom gaps.
- No scrollbars on the stage at any zoom.
- Shortcuts and Ctrl+wheel change zoom; drag/wheel pan only when overflowing.