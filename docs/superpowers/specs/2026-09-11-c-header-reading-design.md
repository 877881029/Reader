# C / Header File Reading (.c / .h)

Date: 2026-09-11  
Status: Implemented (`.c` / `.h` read-only code view with shared C highlighter)  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Reader opens `.c` and `.h` the same way it already opens JSON / YAML / XML: a **read-only** paper code page with VS Code-style line numbers, lightweight syntax highlighting, and copy/select. This is a viewer, not an IDE.

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.

## 2. Decisions

| Topic | Choice |
|---|---|
| Scope | `.c` and `.h` only (no `.cpp` / `.hpp` / `.cc` this round) |
| Interaction | Read-only; mouse/keyboard selection and copy |
| Highlighting | `QSyntaxHighlighter` C rules shared by `.c` and `.h` (keywords, numbers, strings, `//` and `/* */`, preprocessor). No new packages |
| Line numbers / wrap / encoding / theme | Same as existing `CodeTextView` |
| Office / visual | Not applicable |
| Associations | Both suffixes join `sniff.SUPPORTED_EXTENSIONS` and `associate.EXTENSIONS` (Open With + current-user default, like JSON) |

Invalid or incomplete C is still shown as text; highlighting is best-effort, not a compiler.

## 3. Surfaces

- `CODE_SUFFIXES`, sniff, associate, open-dialog filter, welcome badges (`C` / `H`)
- Pipeline `kind="code"` via existing `fmt_code.to_preview`
- `highlighter_for(".c"|".h")` → `CHighlighter`
- Preview cache still skipped for code suffixes
- README / 功能全解 / Ctrl+F scope list the two suffixes

## 4. Non-goals

- C++ / other languages
- Editing, build, clangd, go-to-definition
- Changing JSON / YAML / XML highlighters

## 5. Testing

- Sniff / associate / open dialog / `decide_open` / pipeline accept `.c` and `.h`
- `language_for` maps both to `c`; highlighter is `CHighlighter` and colors a typical snippet
- Existing code-view gutter / read-only tests stay green
- Caption hit tests stay green
