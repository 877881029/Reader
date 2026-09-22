# C++ Source Reading (`.cpp` / `.hpp`)

Date: 2026-09-22
Status: Implementing; Task 1 complete
Progress ledger: `docs/STATUS.md`

## 1. Goal

Reader opens `.cpp` and `.hpp` files through the existing read-only code viewer,
with line numbers, selectable copy, UTF-8 replacement decoding, and the same
C-family syntax highlighting used for `.c` and `.h`.

The two suffixes must behave consistently across direct open, open dialog,
drag/drop, recent files, command-line/IPC open, Windows Open With registration,
and the frozen application.

## 2. Decisions

| Topic | Choice |
|---|---|
| Scope | Add `.cpp` and `.hpp` together; no other C++ suffixes in this increment |
| Preview kind | Existing `kind="code"` pipeline |
| Language | Map both suffixes to the existing `"c"` language family |
| Highlighting | Reuse `CHighlighter`; do not add a parser or dependency |
| Interaction | Read-only, line-numbered, selectable/copyable `CodeTextView` |
| Status | Existing `代码预览` |
| Encoding | Existing UTF-8 decode with invalid bytes replaced |
| Cache | Continue skipping preview cache for code suffixes |
| Associations | Register both suffixes with Reader for the current user |
| UCPD | Do not add either suffix to `PROTECTED_EXTENSIONS` |
| Welcome badges | `CPP` and `HPP` |

## 3. Required Surfaces

- `reader.formats.code.CODE_SUFFIXES` and `language_for`
- `reader.sniff.SUPPORTED_EXTENSIONS`
- preview pipeline dispatch and `decide_open`
- `highlighter_for` / `CodeTextView`
- open-dialog filter
- welcome/recent badges
- `reader.shell.associate.EXTENSIONS`
- README and `docs/Reader功能全解.md`
- frozen smoke telemetry and packaging contracts

All suffix comparisons remain case-insensitive through the existing
`Path.suffix.lower()` behavior.

## 4. Non-goals

- Editing, saving, formatting, compilation, indexing, symbol navigation, or LSP
- A full C++ parser or semantic highlighting
- Additional suffixes such as `.cc`, `.cxx`, `.hh`, `.hxx`, `.inl`, or `.ipp`
- Changes to `.c`, `.h`, `.txt`, JSON, YAML, or XML behavior
- Changes to `hit_test_local`, `begin_window_move`, or `nativeEvent`
- Machine-wide associations or Windows Settings/UCPD claim flow

## 5. Acceptance

1. RED tests first prove `.cpp` and `.hpp` are rejected or missing from every
   required surface.
2. Both suffixes produce `kind="code"`, language `"c"`, `CHighlighter`, and
   status `代码预览`.
3. Open dialog, welcome badges, sniffing, pipeline routing, and current-user
   Open With registration include both suffixes exactly once.
4. A frozen Reader opens representative `.cpp` and `.hpp` files and reports
   document-ready telemetry for each without weakening the existing PPTX,
   Markdown, TXT, or two-batch IPC smoke contracts.
5. The unified fast gate passes after implementation; the release gate passes
   before the feature is marked complete.
