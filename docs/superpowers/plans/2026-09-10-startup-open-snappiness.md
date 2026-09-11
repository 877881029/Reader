# Startup and Open Snappiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** First paint of the welcome window must not wait on registry/COM or Chromium; opening a file must not blank the window; Chromium must stay warm.

**Architecture:** Defer shell integration until the event loop; keep a hidden WebEngine view alive after a delayed warmup; leave the welcome stack up until real preview content exists when the user already saw welcome. File argv launch shows the window only after `open_paths`.

**Tech Stack:** PySide6, QWebEngine, pytest, frozen onedir smoke.

## Global Constraints

- Do not change `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- `READER_SKIP_WEBENGINE_WARMUP` skips scheduling in pytest.

---

### Task 1: First paint before shell integration + keep-alive warmup

- [x] Tests: deferred shell integration; warmup keeps a hidden view
- [x] `__main__.py` `QTimer.singleShot(0, ...)`; `AA_ShareOpenGLContexts`
- [x] `webengine_warmup.py` keep-alive view; delay 400ms; no `processEvents`
- [x] Icons/frame styles from `winId()` before `show`

### Task 2: Welcome stays until preview content exists

- [x] Blocked-open test: stack still welcome while “正在加载…”
- [x] `_refresh_content_stack` / `_install_document_content` changes

### Task 3: Freeze, smoke, shortcut

- [x] Full pytest; `build_windows.ps1`; smoke; desktop `.lnk`; STATUS

### Task 4: File argv launch must not flash welcome

- [x] Hidden `open_paths` uses tabs stack while loading; visible welcome still waits for content
- [x] `new_window(show=False)` then `open_paths` then `show()` when argv has files
- [x] Full pytest; freeze; smoke; desktop shortcut; STATUS
