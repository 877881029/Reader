# Setup Script Includes Frozen Build

Date: 2026-09-11  
Status: Implemented (`setup.ps1` calls `build_windows.ps1` after pip)  
Progress ledger: `docs/STATUS.md`

## 1. Goal

`scripts/setup.ps1` is the one colleague command: create `.venv`, install Reader, **then freeze** `dist\Reader\Reader.exe` by calling the existing `scripts/build_windows.ps1`. Git still does not contain the exe.

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.  
Do **not** duplicate npm/PyInstaller logic inside `setup.ps1`.

## 2. Decisions

| Topic | Choice |
|---|---|
| How | After pip install, `setup.ps1` runs `scripts\build_windows.ps1` (same Bypass / NoProfile). Freeze work stays in `build_windows.ps1` |
| Default | Freeze runs. Needs Node 18+ as today |
| Escape | `-SkipBuild` skips freeze (Python-only source run) |
| Launch | After a successful freeze, start `dist\Reader\Reader.exe`. If freeze was skipped (or exe missing), fall back to `.venv\Scripts\python.exe -m reader` |
| `-SkipLaunch` | Still means: do not start a GUI; freeze still runs unless `-SkipBuild` |
| `-Dev` | Unchanged (`pip install -e ".[dev]"` before freeze) |
| Git | Still no `dist/` / exe in git |

This supersedes the 2026-09-08 rule “setup.ps1 must not call npm / PyInstaller / build_windows.ps1”. The new rule is: setup **must** call `build_windows.ps1`, and must **not** inline npm or PyInstaller.

## 3. Non-goals

- Copying the freeze script body into setup.ps1
- Committing `dist/`
- Changing PyInstaller / web bundle steps

## 4. Testing

- `setup.ps1` contains `build_windows.ps1`, `$SkipBuild`, `$SkipLaunch`, pip install, and a frozen-exe launch path
- `setup.ps1` does not contain `npm` or `PyInstaller` (those stay in `build_windows.ps1`)
- README / 功能全解 / release notes describe one-shot freeze plus `-SkipBuild`
