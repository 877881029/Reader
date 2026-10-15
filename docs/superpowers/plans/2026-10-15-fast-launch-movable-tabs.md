# Fast Launch, New Window per Open, Movable Tabs Implementation Plan

Status: Implemented (2026-10-15)

**Spec:** `docs/superpowers/specs/2026-10-15-fast-launch-movable-tabs-design.md`

## Task 1: Lazy heavy format libraries
RED: importing `reader.preview.pipeline` must not load docx/pptx/openpyxl/numpy.
GREEN: function-level imports.

## Task 2: Fast launcher
RED: launcher forwards to a fake pipe server without importing PySide6; falls
back to `main` when no server; frame/ACK format; spec entry is the launcher.
GREEN: `reader/launcher.py`, `reader.spec`, `__main__` dispatch.

## Task 3: New window per launch
RED: IPC paths open a new window; already-open file focuses its window; empty
launch opens a welcome window. GREEN: `ReaderApp._on_ipc_paths`.

## Task 4: Transfer documents between windows
RED: move dirty Markdown / code / terminal tabs between windows keeps state and
handlers (title `*`, save, live push); source closes when empty; 「移到新窗口」.
GREEN: `MainWindow.detach_document` / `adopt_document`, app-level move helper.

## Task 5: Drag tabs out / onto another window
RED: drag helpers decide tear-off vs drop target. GREEN: `ReaderTabBar` drag,
window drop handling.

## Task 6: Cold start, measurement, docs, release, install