# Notepad-Style Status Bar and Ctrl+J Implementation Plan

Status: Implemented

**Spec:** `docs/superpowers/specs/2026-10-12-status-bar-goto-design.md`

## Task 1: Code page status bar and font/wrap shortcuts

**RED** `test_code_view.py`: replace toolbar tests with status bar tests
(labels, no buttons/spin boxes, position/size/type updates, Ctrl+wheel and
Ctrl+=/-/0 bounded, Alt+Z wrap, readonly notice).
**GREEN** `CodeTextView` bottom status bar, `CodeEditor` Ctrl+wheel hook,
`QShortcut`s.

## Task 2: Ctrl+J go-to-line bar

**RED** window tests replace the dialog tests: Ctrl+J shows `goToLineBar`,
Enter jumps and closes, invalid input message, Esc closes, find/goto bars are
mutually exclusive, ignored without a text page.
**GREEN** `shell/goto_bar.py` + window wiring.

## Task 3: Docs, release gate, install

README, 功能全解, STATUS; `verify.ps1 -Release`; `install_local.ps1`
(covers the binary viewer too).