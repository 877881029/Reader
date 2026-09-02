# Notepad Spacing and Surface Plan

> **For agentic workers:** Use superpowers:executing-plans.

**Goal:** Tight tab/+, soft page color, rounded window, editor flush under chrome.

**Architecture:** Tab cluster spacing 0; `#F9F9F9` page; stretch QTabWidget pane; DWM round corners.

## Constraints

- Do not edit hit-test / `startSystemMove` / `nativeEvent`.
- Commit + push; update STATUS.

### Task 1: Layout + color + pane stretch

- [x] Tests for plus gap, editor-under-chrome, `#f9f9f9`
- [x] Implement cluster, colors, `ChromeTabWidget`, DWM round
- [x] GREEN drag/button tests; commit/push

### Task 2: Frozen certify

- [x] pytest; build; smoke; shortcut
