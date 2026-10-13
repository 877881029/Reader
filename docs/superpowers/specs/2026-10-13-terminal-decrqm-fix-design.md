# Terminal DECRQM Crash Fix Design

Status: Implemented
Progress ledger: `docs/STATUS.md`

## Background

`ghcp` (the user's PowerShell profile function launching GitHub Copilot CLI
1.0.96) works in the Copilot app terminal but shows nothing in Reader.
Investigation:

- The CLI starts and its UI output reaches Reader (~8.5 KB) — PTY and shell are
  fine.
- The page logs `Uncaught ReferenceError: i is not defined`; xterm.js stops
  processing output, never enters the alternate screen and never answers the
  CLI's queries.
- Trigger: DECRQM `ESC[?2026$p` (and any `ESC[?…$p` / `ESC[…$p`). Vite's
  esbuild minifier rewrote xterm.js 6.0.0's `let r; (…)(r ||= {})` in
  `requestMode` into `(void 0 || (i = {}))`, an assignment to an undeclared
  variable that throws in module strict mode. Upstream source is correct.

## Fix

- Build the terminal bundle with `build.minify: false` so the already-minified
  xterm.js is not rewritten. No runtime behaviour change; bundle grows.
- Regression test in real WebEngine: writing DECRQM queries (2026, 1049, 12)
  produces the `ESC[?N;S$y` replies through the bridge without JS errors, and a
  Copilot-CLI-like startup sequence switches xterm to the alternate buffer.
- Static guard: built bundle must not contain `void 0||(i={})`.

## Acceptance

`ghcp` renders the Copilot CLI UI inside Reader's terminal.