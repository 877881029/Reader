# Terminal Tab Implementation Plan

Status: Approved

**Spec:** `docs/superpowers/specs/2026-10-12-terminal-tab-design.md`

## Task 1: TerminalPage

**RED** `tests/test_terminal_page.py`: output of a command, Chinese output,
prompt follows `Set-Location`, markers hidden, history Up/Down, `cls`,
restart, shutdown stops the process.
**GREEN** `src/reader/shell/terminal_page.py`.

## Task 2: Menu wiring

**RED** window: Terminal item enabled, opens `终端` tab in the current file's
folder (home without file), close without prompt.
**GREEN** `MainWindow.add_terminal_tab`.

## Task 3: Docs and release gate

README, 功能全解, STATUS; `verify.ps1 -Release`; spec/plan Implemented.