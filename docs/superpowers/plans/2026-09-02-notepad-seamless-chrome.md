# Notepad Seamless Chrome Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or subagent-driven-development) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the window draggable from the tab chrome, fuse tab row and editor into one white surface, and hide the bottom status bar.

**Architecture:** Add `startSystemMove` on caption handles (with Win32 fallback). Restyle chrome/tab pane/editor to `#ffffff` with no dividers. Hide `QStatusBar` while keeping the in-memory status API.

**Tech Stack:** Python 3.12+, PySide6 Widgets, pytest-qt, Win32 `SendMessage` fallback.

## Global Constraints

- Keep `WS_CAPTION|THICKFRAME|MIN/MAX` for taskbar.
- Do not add File/Edit/View or formatting toolbar.
- `status_text()` remains for tests; the bar is not painted.
- Commit + push each task; update `docs/STATUS.md`.

---

## File Structure

- Modify: `src/reader/shell/title_chrome.py` — move handles, colors, no bottom border
- Modify: `src/reader/shell/window.py` — hide status bar, seamless tab pane, DPI NCHITTEST
- Modify: `src/reader/preview/md_text_view.py` — frameless white editor
- Modify: `tests/test_title_chrome.py`, `tests/test_window.py`, `tests/test_md_text_view.py`
- Modify: `docs/STATUS.md`

---

### Task 1: Caption drag via startSystemMove

**Files:** `title_chrome.py`, `tests/test_title_chrome.py`, `window.py`

- [ ] Failing tests: caption/icon press calls `startSystemMove`; `+` does not
- [ ] Implement move handles + Win32 fallback; DPI-correct NCHITTEST
- [ ] GREEN + commit/push

---

### Task 2: Seamless white chrome + hidden status bar

**Files:** `title_chrome.py`, `window.py`, `md_text_view.py`, tests

- [ ] Failing tests: status bar hidden; chrome/editor same `#ffffff`; no chrome bottom border; editor `NoFrame`
- [ ] Implement styles + hide status bar
- [ ] GREEN + commit/push

---

### Task 3: Regression + frozen certify

- [ ] Full pytest
- [ ] `build_windows.ps1` + `smoke_windows.ps1`
- [ ] Refresh desktop shortcut; STATUS complete + push

## Spec coverage

| Requirement | Task |
|---|---|
| Window drag | 1 |
| Same-color tab/editor, no middle seam | 2 |
| No status bar | 2 |
| Frozen certify | 3 |
