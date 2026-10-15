# Fast Launch, New Window per Open, Movable Tabs Design

Status: Approved
Progress ledger: `docs/STATUS.md`

## Problem (measured on the installed build, 2026-10-15)

- Cold open of a `.txt` from Explorer: 14.1 s until content is shown.
- Second double-click while Reader runs (forwarded to the running instance):
  5.0 s until shown; the short-lived launcher process alone needs ~6–8 s just to
  import modules (`Reader.exe --pty-selftest` measures imports: 5.9–7.8 s).
- Causes: every launch imports python-docx, python-pptx and openpyxl (+numpy)
  through `reader.preview.pipeline` (2.7 s of 3.9 s total import time in the dev
  venv; slower frozen because each DLL/pyd is scanned on load); the launcher
  imports the whole GUI stack before it even checks for a running instance.
- Tabs cannot leave their window; every Explorer open lands in an existing window.

## User decision

Each double-click opens a new window (classic Notepad feel) served by the one
running process; tabs can be dragged between windows or out into a new window.

## Design

1. **Lazy heavy libraries**: `formats/docx.py`, `pptx.py`, `xlsx.py` import
   their libraries inside the functions that need them.
2. **Fast launcher**: new entry `reader/launcher.py` (PyInstaller entry). Before
   any Qt import it tries to hand the command line to a running instance through
   the existing local server pipe (`\\.\pipe\<server name>`) with a ctypes client
   speaking the same frame protocol (4-byte big-endian length + JSON, `ACK`
   reply, 3 s timeout). No running instance → fall through to the normal
   `reader.__main__.main`. `python -m reader` behaves the same.
3. **New window per launch**: IPC requests open a new window (empty launch →
   welcome window). Files already open in any window are focused there instead of
   being opened twice (prevents two editors on one file).
4. **Movable tabs** (same process): a document can be transferred between
   windows without reloading — the page widget, editor/preview, terminal or
   browser keep their state. The source window releases it without disposing,
   the target re-binds its signal handlers; previews still loading are restarted
   in the target. The source window closes when it loses its last tab.
   - Drag a tab out of the window → new window at the cursor.
   - Drag a tab onto another Reader window → moves there.
   - Tab context menu: 「移到新窗口」.
5. **Cold start**: measure after 1–2; defer WebEngine warm-up until the first
   document is shown if it is on the critical path.

## Acceptance

- Installed build: second double-click shows the file in a new window ≤ ~1.5 s;
  launcher process exits quickly; cold open measured before/after.
- Moving a dirty Markdown editor, a live preview, a terminal and a code tab keeps
  their content/state; closing the emptied source window does not prompt.