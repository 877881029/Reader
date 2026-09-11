# SVG Reading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Open `.svg` as a paper-themed, fit-to-pane QtSvg graphic tab.

**Architecture:** Same as native PDF: sniff + pipeline `kind="svg"` + dedicated view. Source path is not copied into the preview cache. `QSvgRenderer` paints the graphic; scripts do not run.

**Tech Stack:** PySide6.QtSvg, pytest-qt, existing paper tokens.

## Global Constraints

- Do not change `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- No new third-party SVG packages.
- User asked to implement without extra approval gates.

---

### Task 1: Sniff, pipeline, view

- [x] Failing tests for `.svg` sniff/open/pipeline/associate/dialog/view
- [x] `formats/svg.py`, `preview/svg_view.py`, `PreviewKind` + `svg_path`
- [x] Wire sniff, associate, pipeline, cache skip, `_default_viewer`, dialog, welcome badge, README, `docs/Reader功能全解.md`, `reader.spec` QtSvg

### Task 2: Freeze

- [x] Full pytest; freeze; smoke; desktop shortcut; STATUS; push `origin/main`
