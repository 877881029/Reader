# Code File Reading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Open JSON / YAML / YML / XML with VS Code-style line numbers and lightweight syntax highlighting.

**Architecture:** Sniff + pipeline `kind="code"`; `CodeTextView` is a paper-themed `QPlainTextEdit` plus gutter; `QSyntaxHighlighter` per language.

**Tech Stack:** PySide6, pytest-qt, existing paper tokens.

## Global Constraints

- Do not change `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- No new third-party highlighter packages.

---

### Task 1: Sniff, pipeline, view

- [x] Failing tests for extensions, pipeline kind, read-only gutter
- [x] `formats/code.py`, `preview/syntax.py`, `preview/code_view.py`
- [x] Wire sniff, associate, pipeline, `_default_viewer`, dialog, welcome badges, README

### Task 2: Freeze

- [x] Full pytest; freeze; smoke; desktop shortcut; STATUS
