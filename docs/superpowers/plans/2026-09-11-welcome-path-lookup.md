# Welcome Path Lookup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Hidden Ctrl+F path lookup on the welcome recent heading; directory lists folders then files; clicking a folder walks one level down.

**Architecture:** `WelcomePage` heading row hosts a hidden `QLineEdit`. Enter classifies path via `Path.is_dir` / `is_file`. Listing reuses `_RecentRow`. `MainWindow` Ctrl+F on welcome calls `show_lookup()` instead of the document FindBar.

**Tech Stack:** PySide6, existing welcome cards, `SUPPORTED_EXTENSIONS`.

## Global Constraints

- Do not change `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- Do not restyle or reorder the left brand column.
- User asked to implement without extra approval gates.

---

### Task 1: Lookup

- [x] Failing tests for Ctrl+F field, directory listing, file open, Esc
- [x] Path helpers + heading-row edit on `WelcomePage`
- [x] Wire `MainWindow` Ctrl+F / Esc; update find spec + 功能全解

### Task 2: Freeze

- [x] Full pytest; freeze; smoke; desktop shortcut; STATUS; push `origin/main`

### Task 3: Folder cards and click-to-enter

- [x] Failing tests: `openable_in_directory` returns folders then files; click folder updates lookup and lists inside without opening a tab
- [x] `openable_in_directory` includes non-hidden dirs; `_RecentRow` badge `DIR`; click folder updates lookup and relists one level
- [x] Full pytest; freeze; smoke; desktop shortcut; STATUS; push `origin/main`
