# Real Terminal (ConPTY + xterm.js) Design

Status: Approved
Progress ledger: `docs/STATUS.md`

## Background

The current Terminal tab is a line-based PowerShell console over pipes: no
colours, no Tab completion, no full-screen programs. The user wants a terminal
"like the Copilot app's right-side terminal", offering **Command Prompt** and
**PowerShell** (normal privileges only — admin modes were dropped after
discussion), with colours matching the Copilot theme.

## Architecture

- **PTY**: `pywinpty` 3.0.5 (ConPTY; bundles `conpty.dll` + `OpenConsole.exe`).
  `reader/terminal/pty_session.py::PtySession(QObject)` spawns the shell with
  the terminal's real cols/rows, reads on a daemon thread, emits `output(str)`
  and `exited(int)`, and supports `write`, `resize`, `shutdown` (force kill).
  Shell profiles use absolute `%SystemRoot%\System32` paths:
  `powershell` → `WindowsPowerShell\v1.0\powershell.exe -NoLogo`,
  `cmd` → `cmd.exe`.
- **Renderer**: offline `web/terminal-viewer` (Vite + TS, `@xterm/xterm` 6.0.0,
  `@xterm/addon-fit` 0.11.0, MIT) built to `assets/terminal-viewer` with
  notices and manifest like the other bundles. `QWebChannel` bridge:
  JS → Python `ready(cols, rows)`, `input(data)`, `resize(cols, rows)`,
  `copyText(text)`; Python → JS `output(data)`, `exited(code)`.
  Output produced before the page is ready is buffered.
- **Isolation**: dedicated off-the-record profile whose request interceptor only
  allows the bundle directory and `qrc:`; no web-link addon, so terminal output
  is never navigable.
- **Theme (Copilot light)**: background `#fbf9f5`, foreground/cursor `#1f1d1a`,
  selection `#e9e3d9`; ANSI palette = GitHub Light (black `#24292f`, red `#cf222e`,
  green `#116329`, yellow `#4d2d00`, blue `#0969da`, magenta `#8250df`,
  cyan `#1b7c83`, white `#6e7781`, bright black `#57606a`, bright red `#a40e26`,
  bright green `#1a7f37`, bright yellow `#633c01`, bright blue `#218bff`,
  bright magenta `#a475f9`, bright cyan `#3192aa`, bright white `#8c959f`);
  font Cascadia Mono / Consolas 13px.

## Behaviour

- `+` → **Terminal** becomes a submenu: **PowerShell**, **Command Prompt**
  (icons). Tab title = profile name. Start directory: folder of the current
  real file, else home.
- Fit to tab size on open and resize; keystrokes go to the shell. `Ctrl+C`
  copies when text is selected, otherwise interrupts; `Ctrl+V` pastes.
- While a terminal tab is current, Reader's Ctrl-letter document shortcuts
  (`Ctrl+O/F/H/J/G/I/T/S/Shift+S/N`) are disabled so the keys reach the shell.
- When the shell exits: `[进程已退出，按 Enter 重新启动]`; Enter restarts the
  same profile. Closing the tab/window kills the process; no unsaved prompt.
- Frozen build: `Reader.exe --pty-selftest <file>` spawns `cmd /c echo` through
  ConPTY and writes the result; frozen smoke runs it.

## Non-goals

- Administrator shells, multiple panes, shell profile editing, web links.

## Acceptance

- Unit tests for `PtySession` (output, Chinese input, resize, exit, shutdown),
  web tests for theme and bridge wiring, real WebEngine test that a typed
  command's output reaches the xterm buffer, menu/shortcut tests, frozen
  selftest in smoke.