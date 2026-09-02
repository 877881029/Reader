# Notepad Chrome Hit-Test Repair Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix button clicks, repeatable window move, correct resize hit-testing, and Notepad gray/white colors.

**Architecture:** `HTCLIENT` for all Qt chrome; `startSystemMove` only for drag; `ScreenToClient` + DPR for borders; `#F3F3F3` title vs `#FFFFFF` editor.

**Tech Stack:** Python, PySide6, Win32, pytest-qt.

## Global Constraints

- Keep `WS_CAPTION|THICKFRAME` for the taskbar.
- No `HTCAPTION` / `HTMINBUTTON` / `HTMAXBUTTON` / `HTCLOSE` from our hit-test.
- No `WM_NCLBUTTONDOWN` fallback.
- Commit + push; update `docs/STATUS.md`.

---

### Task 1: Hit-test + repeatable move

- [x] Tests: buttons/caption `HTCLIENT`; two caption presses; max button still triggers
- [x] `hit_test_local` + `ScreenToClient`; `begin_window_move` ReleaseCapture + startSystemMove only
- [x] GREEN + commit/push

### Task 2: Notepad gray title / white page

- [x] Tests: chrome `#f3f3f3`; editor `#ffffff`
- [x] Styles
- [x] GREEN + commit/push

### Task 3: Frozen certify

- [x] pytest (`327 passed, 1 skipped`)
- [x] build; smoke; shortcut; STATUS
