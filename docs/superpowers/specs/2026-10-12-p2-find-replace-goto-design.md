# P2 Find/Replace and Go To Line Design

Status: Implemented
Progress ledger: `docs/STATUS.md`

## Background

P1 made TXT/MD/JSON/YAML/XML/C/C++ editable. Notepad's next most used
features are `Ctrl+H` replace and `Ctrl+G` go to line; Reader has neither as a
window-level command.

## Scope

1. **Replace (`Ctrl+H`)** — the existing find bar gains a replace field and
   `替换` / `全部替换` buttons (hidden in plain find mode). Enabled only when
   the current tab is an editable text page (`CodeTextView` or Markdown text
   mode, not read-only/lossy). `替换` replaces the current match if the
   selection equals the query (respecting `Aa`), then moves to the next match.
   `全部替换` replaces every match in one undo step and reports
   `已替换 N 处` / `未找到` in the bar. Edits mark the tab dirty like typing.
2. **Go to line (`Ctrl+G`)** — prompts for a 1-based line (default current,
   range 1..line count) and moves the caret to the line start, centred.
   Works on every plain-text page including read-only ones. The prompt is
   injectable (`MainWindow.goto_line_prompt`); default `QInputDialog.getInt`
   titled `转到行`.

## Non-goals

- Regex, whole-word, replace inside rendered/HTML/PDF/WebEngine pages.

## Acceptance

- `Ctrl+H` on an editable page shows the replace row; on a read-only or
  non-text page it does nothing.
- Replace / replace-all honour case sensitivity, are undoable, and dirty the tab.
- `Ctrl+G` jumps to the requested line; cancel leaves the caret unchanged.