# P2 Find/Replace and Go To Line Implementation Plan

Status: Approved

**Spec:** `docs/superpowers/specs/2026-10-12-p2-find-replace-goto-design.md`

## Task 1: Replace primitives

**RED** `tests/test_find_replace.py`: `replace_current` replaces only a
matching selection and advances; `replace_all` counts, honours case, is one
undo step, and returns 0 on read-only editors.
**GREEN** `find_support.replace_current` / `replace_all`.

## Task 2: Ctrl+H replace row in the window

**RED** window tests: shortcut, replace row visibility, replace-all on a
TXT tab dirties it and reports the count, read-only tab ignored.
**GREEN** `FindBar` replace mode + `actionReplace`.

## Task 3: Ctrl+G go to line

**RED** window tests: jumps on code and Markdown text pages, cancel keeps
caret, welcome/no text page ignored.
**GREEN** `actionGoToLine` with injectable prompt.

## Task 4: Docs

README, 功能全解 shortcuts and find section; STATUS; spec/plan Implemented.