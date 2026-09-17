# Open / Resize / Cold-Start Snappiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faster first launch after boot, no welcome flash on Explorer open, less black-frame wait on open/resize.

**Architecture:** Keep per-document WebEngine profiles. Defer PDF Settings claim; start warmup immediately on file argv; treat visual/WebEngine widgets as unready until `ready`/`loadFinished`; lazy PPTX text fallback; coalesce resize stretches.

**Tech Stack:** PySide6, existing preview worker, pytest-qt.

## Global Constraints

- Do not change `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- Do not share one `QWebEngineProfile` across documents.
- Do not add a splash executable.
- User asked to implement without extra approval gates.

---

### Task 1: Launch, welcome, warmup, claim

**Files:** `src/reader/__main__.py`, `src/reader/preview/webengine_warmup.py`, `src/reader/shell/window.py`, `tests/test_main_launch.py`, `tests/test_window.py`, `tests/test_webengine_warmup.py`, `tests/test_packaging.py`

- [x] Failing tests for delay_ms=0, delayed claim, welcome suppressed on file show
- [x] Implement those launch paths
- [x] Tests pass

### Task 2: Ready-before-leave-welcome, lazy PPTX fallback, resize coalesce

**Files:** `src/reader/shell/window.py`, `src/reader/formats/pptx.py`, `src/reader/preview/pptx_view.py`, matching tests

- [x] Failing tests for ready gate and `to_visual` without extract
- [x] Implement ready property, lazy fallback, resize timer
- [x] Tests pass

### Task 3: Docs, freeze, push

- [x] 功能全解 + STATUS
- [x] Full pytest; freeze; smoke; shortcut; push `origin/main`
