# Stable Local Install and Shortcut Refresh Design

Status: Approved
Progress ledger: `docs/STATUS.md`

## Background

The user could not find the latest Reader on the desktop. Root causes:

1. `create_desktop_shortcut` never touches an existing `Reader.lnk`, so a
   shortcut to an older build (here the main checkout `dist`) is never refreshed.
2. New builds live in throwaway worktree `dist` folders; there is no stable
   install location or install step.

## Scope

- `create_desktop_shortcut(overwrite=False)` refreshes an existing shortcut only
  when its current target file name is `Reader.exe`, the new exe file name is
  `Reader.exe`, and the two paths differ (case-insensitive). Shortcuts to other
  programs and dev launches (`python.exe -m reader`) never rewrite it.
- `scripts/install_local.ps1 [-Source dist\Reader] [-Destination
  %LOCALAPPDATA%\Programs\Reader]`: refuses if Reader is running from the
  destination, mirrors the build, verifies the exe hash matches, then runs the
  installed exe's own registration (file associations + desktop shortcut with
  overwrite) via the dev Python, printing the shortcut target.

## Acceptance

- Unit tests cover refresh / same target / foreign target / dev python cases.
- Running the script leaves `Desktop\Reader.lnk` and `Reader.Document` open
  command pointing at `%LOCALAPPDATA%\Programs\Reader\Reader.exe`.