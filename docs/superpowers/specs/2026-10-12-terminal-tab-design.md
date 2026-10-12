# Terminal Tab Design

Status: Approved
Progress ledger: `docs/STATUS.md`

## Background

The `+` menu lists **Terminal** as a disabled placeholder. The user asked to
implement it: a simple PowerShell console in a Reader tab.

## Scope

- `+` → **Terminal** opens a `终端` tab (`TerminalPage`, object name
  `terminalPage`): read-only monospace output (`terminalOutput`), a prompt
  label showing the current directory (`terminalPrompt`) and a command line
  (`terminalInput`), plus `清屏` / `重启` buttons.
- Backend: `%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe
  -NoLogo -NoProfile -NoExit -Command -` via `QProcess` with merged
  stdout/stderr. Startup lines switch console input/output encoding to UTF-8
  so Chinese text round-trips. Line-based (pipes, not a PTY): full-screen TUI
  programs are out of scope.
- After every submitted command Reader sends a hidden marker line that prints
  `\x1e` + `$PWD`; marker lines are stripped from output and update the prompt.
- `cls` / `clear` clear the output locally; Up/Down walk command history;
  `重启` kills and restarts the shell in the same directory.
- Start directory: folder of the current tab's real file, else the user home.
- Closing the tab or window kills the process; no unsaved prompt; not recorded
  in recent files. When the process exits, a `[进程已退出]` line is shown.

## Non-goals

- PTY/ConPTY, colours/ANSI rendering, tabs completion, multiple shells.

## Acceptance

- Commands run and their output (including Chinese) appears.
- `Set-Location` updates the prompt; markers never appear in output.
- History, `cls`, restart and shutdown behave as above.
- Menu item enabled; terminal tab opens in the current document's folder.