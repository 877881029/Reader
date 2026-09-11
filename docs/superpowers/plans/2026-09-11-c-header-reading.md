# C / Header File Reading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Open `.c` and `.h` in the existing read-only code view with a shared C highlighter.

**Architecture:** Add the suffixes to `CODE_SUFFIXES` / sniff / associate. Reuse `kind="code"` and `CodeTextView`. Add `CHighlighter` and route `.c`/`.h` through `highlighter_for`.

**Tech Stack:** PySide6 `QSyntaxHighlighter`, existing paper tokens.

## Global Constraints

- Do not change `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- No new third-party highlighter packages.
- User asked to implement without extra approval gates.

---

### Task 1: Suffixes, highlighter, wiring

**Files:**
- Modify: `src/reader/formats/code.py`, `src/reader/preview/syntax.py`, `src/reader/sniff.py`, `src/reader/shell/associate.py`, `src/reader/preview/pipeline.py`, `src/reader/shell/window.py`, `src/reader/shell/welcome.py`
- Test: `tests/test_formats_code.py`, `tests/test_code_view.py`, `tests/test_sniff.py`, `tests/test_open.py`, `tests/test_pipeline.py`, `tests/test_associate.py`, `tests/test_window.py`, `tests/test_packaging.py`

- [x] Failing tests for `.c`/`.h` sniff, pipeline kind, C highlighter, dialog/associate lists
- [x] Minimal production wiring + `CHighlighter`
- [x] README / 功能全解 / find + default-app spec lists

### Task 2: Freeze

- [x] Full pytest; freeze; smoke; desktop shortcut; STATUS; push `origin/main`
