# Notepad-Style Status Bar and Ctrl+J Go To Line Design

Status: Approved
Progress ledger: `docs/STATUS.md`

## Background

The code/text page has a top toolbar (line spin, 跳转, 换行, A-/A+, size label,
position). The user wants it replaced by a Notepad-like bottom status bar that
only displays information, and jump-to-line on `Ctrl+J` working like `Ctrl+F`.

## Scope

1. `CodeTextView` removes the top toolbar and gains a bottom status bar
   (`codeStatusBar`) at the window's lower edge: plain labels separated by thin
   vertical rules, no buttons, no focus, no click behaviour:
   `Ln 87, Col 19` (`codeStatusPosition`) | `Size 12 pt` (`codeStatusSize`) |
   `Type JSON` (`codeStatusType`), plus `只读` (`codeReadOnlyNotice`) on the right
   only for lossy files. Type names: JSON, YAML, XML, C, C++, C/C++ Header,
   Plain text (fallback: upper-case suffix).
2. Font size (8–24 pt, default 12): `Ctrl+wheel`, `Ctrl+=`/`Ctrl++`, `Ctrl+-`,
   `Ctrl+0` reset, scoped to the code page. Wrap toggle: `Alt+Z`.
3. `Ctrl+J` (with `Ctrl+G` kept as alias) opens a go-to-line bar in the same
   place and style as the find bar (`goToLineBar`): placeholder
   `转到行（1–N）`, Enter jumps (clamped) and closes, Esc/× closes, non-numbers
   show `无效行号`. Opening one bar hides the other. Works on every plain-text
   page (code/TXT and Markdown edit mode); ignored elsewhere. The previous
   `QInputDialog` prompt is removed.

## Non-goals

- Status bar for rendered Markdown/PPTX/PDF/hex pages; encoding/newline items.

## Acceptance

- No buttons or spin boxes remain on the code page; status labels update with
  the caret, font size and file type.
- Font shortcuts and Ctrl+wheel change size within bounds and update the bar.
- Ctrl+J bar jumps, validates, and closes as described.