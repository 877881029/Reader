# Code File Reading (JSON / YAML / XML)

Date: 2026-09-10  
Status: Implemented (JSON / YAML / YML / XML read-only view with line numbers and QSyntaxHighlighter)  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Reader can open `.json`, `.yaml`, `.yml`, and `.xml` as readable code pages: paper theme, **left gutter line numbers** (VS Code-style), **syntax highlighting**, copy/select allowed. This is a viewer, not an IDE.

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.

## 2. Decisions

| Topic | Choice |
|---|---|
| Scope | `.json` `.yaml` `.yml` `.xml` only |
| Interaction | Read-only; mouse/keyboard selection and copy |
| Highlighting | `QSyntaxHighlighter` (no Pygments / extra dependency) |
| Line numbers | `QPlainTextEdit` extra area, right-aligned, width grows with digit count |
| Wrap | Off (horizontal scroll), like VS Code default |
| Encoding | UTF-8, `errors="replace"` |
| Theme | Paper / chrome / ink / cobalt tokens |
| Office / visual | Not applicable; builtin code view only |

`.yml` and `.yaml` share the YAML highlighter.

Invalid JSON/XML is still shown as text; highlighting is best-effort, not a validator.

## 3. Surfaces

- `sniff.SUPPORTED_EXTENSIONS` and `associate.EXTENSIONS`
- Open dialog filter; welcome recent badges (`JSON` / `YAML` / `XML`)
- Pipeline returns `PreviewResult(kind="code", html=<file text>)`
- `_default_viewer` builds `CodeTextView`
- Preview cache skips these suffixes (source file is already local)

## 4. Testing

- Sniff / associate / open dialog / pipeline accept the four suffixes
- Code view is read-only, shows matching line-number width, attaches a highlighter
- Highlighter does not crash on typical snippets
- Caption hit tests stay green
- Frozen smoke still passes; README lists the new formats
