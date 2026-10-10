# Notepad-Class Text Editing (P1) Implementation Plan

Status: Implemented

> Execute tasks in order. For each task: observe RED, implement GREEN, run the
> focused suite, update `docs/STATUS.md`, commit, and push `origin/main` before
> starting the next task.

**Goal:** Make TXT, Markdown text mode, JSON, YAML, XML and C/C++ files
editable and savable with Notepad-equivalent lifecycle and lossless encoding.

**Spec:** `docs/superpowers/specs/2026-09-24-notepad-text-editing-design.md`

**Environment:** Windows, Python `C:\venvs\reader-076ca44a\Scripts\python.exe`.

## Guardrails

- Do not modify `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- Keep `PROTECTED_EXTENSIONS` as `.pdf/.txt`.
- Never write a file Reader could not decode losslessly.
- Keep existing reading toolbar behaviour and frozen smoke contracts.

## Task 1: Lossless text I/O module

**RED** `tests/test_text_io.py`: round trip of UTF-8, UTF-8 BOM, UTF-16 LE/BE
BOM, GB18030, CRLF/LF/CR, empty file default CRLF, lossy bytes flagged
`lossless=False`, text normalised to `\n`, atomic write leaves the original
intact when encoding fails mid-write.

**GREEN** `src/reader/text_io.py` with `TextFile`, `read_text_file`,
`write_text_file`, `default_text_file()`.

## Task 2: Editable code/text view

**RED** `tests/test_code_view.py`: `load_path` view is editable, undo stack
empty and clean after load, typing marks dirty and `*name` title, `save()`
writes through `text_io` and clears dirty, `save_as` changes path/suffix
highlighter, `load_untitled(".txt")`, lossy file is read-only with notice.

**GREEN** `CodeTextView` editing state; `_default_viewer` loads code results
through `load_path` so the view knows its file.

## Task 3: Markdown text view preserves encoding

**RED** `tests/test_md_text_view.py` (or existing suite): CRLF + UTF-8 BOM and
GB18030 Markdown save keep their bytes; lossy Markdown stays read-only.

**GREEN** `MarkdownTextView` load/save through `text_io`.

## Task 4: Window save, Save As, new text, dirty titles

**RED** `tests/test_window.py`: `Ctrl+S` saves a dirty TXT/JSON tab; dirty
`*` tab title for code tabs; `Ctrl+Shift+S` saves code and Markdown tabs to a
new path and retitles; `Ctrl+N` creates an untitled `.txt` editable tab whose
save goes through Save As.

**GREEN** `actionSave` handles both view types; new `actionSaveAs`
(`QKeySequence.StandardKey.SaveAs`) and `actionNewText`
(`QKeySequence.StandardKey.New`).

## Task 5: Unsaved-change protection

**RED** `tests/test_window.py`: closing a dirty tab asks once; Save writes and
closes, Discard closes without writing, Cancel keeps the tab; window close
with any dirty tab honours the same choices and Cancel ignores the close
event; clean tabs close without prompting.

**GREEN** a single `_confirm_discard(document_id)` helper using an injectable
prompt, used by `close_tab` and `closeEvent`.

## Task 6: Docs and release gate

Update `README.md` and `docs/Reader功能全解.md`; run
`scripts\verify.ps1 -Release`; record evidence in `docs/STATUS.md`; mark spec
and plan Implemented.
