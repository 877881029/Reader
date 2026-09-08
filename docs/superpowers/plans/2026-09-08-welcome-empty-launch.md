# Empty Launch Welcome Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. User asked to implement now without extra review gates.

**Goal:** Empty desktop launch shows a zero-tab welcome page with recents and version; plus creates untitled Markdown; taskbar icons stay the blue R.

**Architecture:** Stop auto-draft in `__main__`. Welcome widget on the empty stack page. JSON recents under LOCALAPPDATA. Reapply WM_SETICON on the next tick after show.

**Tech Stack:** PySide6, pytest-qt.

## Global Constraints

- Do not edit `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- Keep `emptyWindowHint` for drop-hint tests.
- Version is `0.1.0` from `VERSION`.
- Commit + push; update STATUS.

---

### Task 1: Empty launch + welcome + recents + SETICON tick

- [x] Tests then implementation
- [x] Full pytest `357 passed, 1 skipped`
- [x] Frozen smoke PPTX/MD/IPC
- [x] Desktop shortcut refreshed with `overwrite=True`

Commit: `feat: show welcome page instead of untitled draft on empty launch`
