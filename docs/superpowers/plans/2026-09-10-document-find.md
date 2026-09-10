# Document Find Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Notepad-style Ctrl+F find bar for every open document tab.

**Architecture:** Window-level `FindBar` plus a small `find_in_widget` helper. Plain text uses `QPlainTextEdit.find`; WebEngine uses `findText`.

**Tech Stack:** PySide6, pytest-qt, existing paper tokens.

## Global Constraints

- Do not change `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- Do not put the find bar inside a tab page layout (`layout.count()` stays 1).
- No replace. No new third-party packages.

---

### Task 1: Helper + find bar + window shortcut

- [x] Failing tests for wrap/case, Ctrl+F show/hide, next match
- [x] `preview/find_support.py`, `shell/find_bar.py`, wire `MainWindow`
- [x] README mentions Ctrl+F

### Task 2: Freeze

- [x] Full pytest; freeze; smoke; desktop shortcut; STATUS
