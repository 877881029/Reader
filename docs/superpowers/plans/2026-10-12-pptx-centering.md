# PPTX Slide Centering Implementation Plan

Status: Approved

**Spec:** `docs/superpowers/specs/2026-10-12-pptx-centering-design.md`

## Task 1: Centred canvas, gutter fit, no scrollbars

**RED** `viewer.test.ts`: canvas left/top centred for fit and for 400% zoom;
fit uses 16px gutter; stylesheet stage `overflow: hidden`.
**GREEN** canvas wrapper + layout function in `viewer.ts`, CSS.

## Task 2: Zoom shortcuts and pan

**RED** Ctrl+= / Ctrl+- / Ctrl+0 / Ctrl+wheel change zoom and prevent default;
wheel and drag pan only when overflowing and are clamped; fit resets pan.
**GREEN** handlers in `viewer.ts`.

## Task 3: Bundle, release gate, docs

`npm run build` (committed bundle + manifest), real WebEngine screenshot check,
`verify.ps1 -Release`, `install_local.ps1`, docs, STATUS.