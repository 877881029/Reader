# Stable Local Install and Shortcut Refresh Implementation Plan

Status: Approved

**Spec:** `docs/superpowers/specs/2026-10-12-local-install-design.md`

## Task 1: Refresh stale Reader shortcuts

**RED** `tests/test_associate.py`: stale Reader.exe target refreshed; same
target untouched; foreign target untouched; python.exe launcher untouched.
**GREEN** `associate.create_desktop_shortcut`.

## Task 2: install_local.ps1

**RED** `tests/test_packaging.py` static contract: script exists, ASCII only,
uses `robocopy /MIR`, hash check, `register_open_with` and
`create_desktop_shortcut(... overwrite=True)`.
**GREEN** script; run it on this machine; README release section; STATUS.