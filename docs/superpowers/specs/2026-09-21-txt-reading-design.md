# Plain Text Reading (.txt)

Date: 2026-09-21  
Status: Implemented (`.txt` read-only text view; current-user default including Settings claim)  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Reader opens `.txt` as a **read-only** paper page with VS Code-style line numbers, selectable copy, and UTF-8 (invalid bytes replaced). Double-clicking a `.txt` for the current Windows user opens **Reader**, not Notepad.

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.

## 2. Decisions

| Topic | Choice |
|---|---|
| Scope | `.txt` only (no `.log` / `.ini` / `.csv` this round) |
| Interaction | Read-only; mouse/keyboard selection and copy. Not a Notepad clone; no save/edit |
| Highlighting | No language highlighter. `highlighter_for(".txt")` must **not** fall through to JSON |
| Line numbers / wrap / encoding / theme | Same as existing `CodeTextView` |
| Status | `文本预览` (keep `代码预览` for JSON/YAML/XML/C) |
| Office / visual | Not applicable |
| Associations | `.txt` joins `sniff.SUPPORTED_EXTENSIONS` and `associate.EXTENSIONS` |
| Default app | Windows often UCPD-locks `.txt` UserChoice the same way as `.pdf`. Add `.txt` to `PROTECTED_EXTENSIONS` so Settings UI can claim it when AssocQueryString is not already Reader |

This is a viewer, not an editor. Invalid encoding is still shown as text.

## 3. Surfaces

- `CODE_SUFFIXES`, sniff, associate, open-dialog filter, welcome badge (`TXT`)
- Pipeline `kind="code"` via existing `fmt_code.to_preview`
- `language_for(".txt")` → `"text"`; `highlighter_for(".txt")` → pass-through highlighter
- Preview cache still skipped for code suffixes
- README / 功能全解 / Ctrl+F / default-app spec list `.txt`

## 4. Non-goals

- Editing, wrap-as-default, encoding picker
- Other plain suffixes (`.log`, `.ini`, `.csv`)
- Changing JSON / YAML / XML / C highlighters

## 5. Testing

- Sniff / associate / open dialog / `decide_open` / pipeline accept `.txt`
- `language_for` maps `.txt` to `text`; highlighter is not `JsonHighlighter`; a JSON-looking `.txt` is not JSON-colored
- `PROTECTED_EXTENSIONS` includes `.txt`; claimer invokes `.txt` when it is not Reader
- Existing code-view gutter / read-only tests stay green
- Caption hit tests stay green
