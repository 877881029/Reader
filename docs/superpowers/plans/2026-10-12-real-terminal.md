# Real Terminal Implementation Plan

Status: Approved

**Spec:** `docs/superpowers/specs/2026-10-12-real-terminal-design.md`

## Task 1: PtySession and shell profiles
RED `tests/test_pty_session.py`; GREEN `reader/terminal/pty_session.py`;
add `pywinpty==3.0.5` dependency.

## Task 2: terminal-viewer web bundle
RED vitest (theme constants, bridge wiring with a fake Terminal, copy/paste key
handling, dispose); GREEN `web/terminal-viewer`, built bundle, notices,
manifest; hygiene test covers the new bundle.

## Task 3: TerminalPage on WebEngine
RED real WebEngine test (typed command output reaches xterm buffer; buffered
early output; exit + Enter restart; shutdown kills); GREEN new `TerminalPage`
with bridge and offline interceptor, replacing the pipe console.

## Task 4: Menu, shortcut passthrough
RED window tests (Terminal submenu with PowerShell / 命令提示符, titles, cwd,
document shortcuts disabled on terminal tabs and restored elsewhere);
GREEN wiring.

## Task 5: Packaging, smoke, docs, release
`reader.spec` (winpty binaries + bundle), `build_windows.ps1`, `verify.ps1`,
`--pty-selftest` + frozen smoke stage, README/功能全解, STATUS,
`verify.ps1 -Release`, `install_local.ps1`.