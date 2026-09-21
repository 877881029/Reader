# Plain Text Reading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Open `.txt` in the existing read-only code view with no language highlighter, and claim it as the current-user default (including UCPD Settings claim).

**Architecture:** Add `.txt` to `CODE_SUFFIXES` / sniff / associate. Reuse `kind="code"` and `CodeTextView`. Route `.txt` through a pass-through highlighter. Add `.txt` to `PROTECTED_EXTENSIONS`.

**Tech Stack:** PySide6 `QSyntaxHighlighter`, existing paper tokens, existing Settings claimer.

## Global Constraints

- Do not change `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- No new third-party highlighter packages.
- User asked to implement without extra approval gates.

---

### Task 1: Suffixes, plain highlighter, default-app claim

**Files:**
- Modify: `src/reader/formats/code.py`, `src/reader/preview/syntax.py`, `src/reader/sniff.py`, `src/reader/shell/associate.py`, `src/reader/preview/pipeline.py`, `src/reader/shell/window.py`, `src/reader/shell/welcome.py`, `src/reader/shell/settings_claim.py`
- Test: `tests/test_formats_code.py`, `tests/test_code_view.py`, `tests/test_sniff.py`, `tests/test_open.py`, `tests/test_pipeline.py`, `tests/test_associate.py`, `tests/test_window.py`, `tests/test_packaging.py`, `tests/test_settings_claim.py`
- Docs: README, `docs/Reader功能全解.md`, default-app and find specs

- [x] Failing tests for `.txt` sniff, pipeline kind, plain highlighter, dialog/associate lists, protected claim
- [x] Minimal production wiring + pass-through highlighter + `PROTECTED_EXTENSIONS`
- [x] README / 功能全解 / find + default-app spec lists

### Task 2: Freeze

- [x] Full pytest; freeze; smoke; desktop shortcut; STATUS; push `origin/main`
