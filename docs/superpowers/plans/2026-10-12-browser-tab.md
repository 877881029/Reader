# Browser Tab Implementation Plan

Status: Implemented

**Spec:** `docs/superpowers/specs/2026-10-12-browser-tab-design.md`

## Task 1: Address normalisation

**RED** `tests/test_browser_page.py` table tests for `normalize_address`.
**GREEN** `src/reader/shell/browser_page.py::normalize_address`.

## Task 2: BrowserPage widget and menu wiring

**RED** browser page loads a local file URL, title/address signals update;
window menu Browser enabled, adds focused tab, title follows page, close
disposes without prompt, not in recent.
**GREEN** `BrowserPage` + `MainWindow.add_browser_tab`.

## Task 3: Docs

README, 功能全解, STATUS; spec/plan Implemented.