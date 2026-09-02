# Notepad Title Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.

**Goal:** Gray Notepad title strip, white selected tab matching the editor, button hover — without touching drag/hit-test.

**Architecture:** Stop white stylesheet leak; paint chrome/buttons gray; selected tab white and flush.

**Tech Stack:** PySide6 stylesheets, pytest-qt.

## Global Constraints

- Do not edit `hit_test_local`, `begin_window_move`, `lparam_to_local`, or `nativeEvent`.
- Keep min/max/close clickable and caption `startSystemMove` tests green.
- Commit + push; update `docs/STATUS.md`.

---

### Task 1: Styles + leak fix

- [x] Tests for gray chrome, white selected tab, hover rules, `#readerRoot`
- [x] Stylesheet changes only
- [x] GREEN hit-test + chrome tests; commit/push

### Task 2: Frozen certify

- [ ] Full pytest; build; smoke; shortcut
