# Notepad-Class Text Editing (P1)

Date: 2026-09-24
Status: Implemented
Progress ledger: `docs/STATUS.md`

## 1. Goal

Close the largest usability gap against Windows Notepad: plain-text and code
files are currently read-only. P1 makes every text-like format Reader opens
(`.txt`, `.md` text mode, `.json`, `.yaml/.yml`, `.xml`, C/C++ family) safely
editable and savable with Notepad-equivalent file lifecycle behaviour.

The user approved P1 with the explicit requirement that it covers TXT, MD,
JSON and the other text formats uniformly, not TXT alone.

## 2. Gap baseline (2026-09-24)

| Notepad capability | Reader before P1 |
|---|---|
| Edit and save text/code | Markdown text mode only; TXT/JSON/YAML/XML/C/C++ read-only |
| New document | `+` creates untitled Markdown only |
| Save As | Untitled Markdown only |
| Undo / redo | Markdown only (Qt built-in) |
| Unsaved-change protection | None: closing a tab or window discards edits |
| Encoding preservation | Read as UTF-8 with replacement; Markdown always saved UTF-8 LF |

## 3. Scope

### 3.1 Lossless text I/O (`reader.text_io`)

- `read_text_file(path) -> TextFile` returning `text`, `encoding`, `bom`,
  `newline`, `lossless`.
- Detection order: UTF-8 BOM, UTF-16 LE/BE BOM, strict UTF-8, strict
  GB18030 (common Chinese legacy files). Anything else decodes as UTF-8 with
  replacement and `lossless=False`.
- Newline style: the first of `\r\n`, `\n`, `\r` found; default `\r\n` for
  empty or single-line files (Windows Notepad default).
- In-memory text always uses `\n`.
- `write_text_file(path, text, fmt)` re-applies the original encoding, BOM and
  newline style and writes atomically (temp file in the same directory then
  `os.replace`), so a failed write never truncates the original.
- Round-trip guarantee: reading then writing unchanged text reproduces the
  original bytes for every lossless file.

### 3.2 Editable code/text view

- `CodeTextView` becomes directly editable (Notepad behaviour: no separate
  edit mode) while keeping line numbers, highlighting, and the existing
  reading toolbar.
- Loading a file never leaves undo history and never marks the view dirty.
- Undo/redo use the editor's built-in `Ctrl+Z` / `Ctrl+Y`.
- Exposes `path`, `dirty`, `dirty_changed`, `path_changed`, `display_title()`
  (`*name` when dirty), `save()`, `save_as(path)`, `load_untitled(suffix)`.
- Files with `lossless=False` open read-only with a visible toolbar notice
  `只读：无法无损识别编码`, so Reader never silently corrupts bytes.
- `MarkdownTextView` uses the same `text_io` for load/save, so Markdown also
  preserves encoding, BOM, and newline style.

### 3.3 Window file lifecycle

- `Ctrl+S` saves the current Markdown text or code/text tab; untitled tabs
  fall through to Save As.
- `Ctrl+Shift+S` Save As for both view types; the dialog default keeps the
  current suffix and offers text/Markdown/JSON/YAML/XML/C/C++/All filters.
- `Ctrl+N` creates an untitled `.txt` code/text tab; the existing `+` button
  keeps creating untitled Markdown.
- Tab titles show `*` while dirty for every editable tab.
- Closing a dirty tab, or the window while any tab is dirty, asks
  `保存 / 不保存 / 取消`. Cancel aborts the close; a cancelled Save As also
  aborts it.
- After Save As to a new path the tab title, document path and recent list
  update; highlighting follows the new suffix.

## 4. Non-goals (later phases)

- Find/replace, `Ctrl+G`, `Ctrl+wheel` zoom, status bar (P2).
- Manual encoding selection or newline conversion UI (P3).
- Large-file streaming, printing, session restore, startup tuning (P4).
- JSON/YAML/XML validation, formatting, auto-indent, LSP.
- Editing PDF/Office/SVG/image formats.

## 5. Constraints

- Strict TDD per `docs/superpowers/process.md`; one atomic commit per task,
  pushed to `origin/main`.
- Do not modify `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- `PROTECTED_EXTENSIONS` stays `.pdf/.txt`.
- Existing frozen smoke contracts (PPTX, MD, TXT, 8 C++ suffixes, exact
  two-batch IPC) must stay green; the release gate runs once at the end.

## 6. Acceptance

- Unit tests prove lossless round trip for UTF-8, UTF-8 BOM, UTF-16 LE/BE,
  GB18030, CRLF/LF/CR, and atomic write failure safety.
- Widget tests prove edit → dirty → save → clean for TXT, JSON, and Markdown,
  undo after load is empty, and lossy files are read-only.
- Window tests prove `Ctrl+S`, `Ctrl+Shift+S`, `Ctrl+N`, dirty titles, and
  save/discard/cancel prompts for tab and window close.
- `scripts\verify.ps1 -Release` passes.
