# Markdown Visual-Default Open and Keyboard Toggle Design

Date: 2026-09-03  
Status: Approved by user (continuous execute; drag/buttons must stay working)  
Depends on: `docs/superpowers/specs/2026-09-01-markdown-edit-chrome-design.md`  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Opening an existing `.md` file shows the **read-only rendered preview**, not the source editor.

New untitled drafts stay **editable**. Saving does **not** auto-switch to preview. Closing the tab and opening the file again uses preview.

Keyboard toggle (Markdown tabs only):

- **Ctrl+I**: preview → immediately editable source
- **Ctrl+S**: save (unchanged)
- **Ctrl+T**: source → preview; if unsaved, force-save first (Save As when there is no path). Cancelled Save As stays in the editor.

Do **not** add title-bar or menu buttons for the toggle. Do **not** bind Ctrl+I / Ctrl+T on PPTX. Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.

## 2. Current behavior

`MainWindow._start_preview` short-circuits `.md` into `_open_markdown_text_tab` unless `READER_SMOKE_MD_VISUAL` is set. The pipeline already defaults `.md` to visual. Switching to visual while dirty and path-less shows “请先保存后再切换视觉预览” and aborts. Restoring text loads `editable=False` (click-to-edit).

## 3. Architecture

- Existing `.md` open (dialog, drop, argv, IPC, wikilink) uses the same visual `_start_preview` path as PPTX. Drop the text-editor short-circuit. `READER_SMOKE_MD_VISUAL` may remain as a no-op override.
- `+` / empty launch still call `add_untitled_markdown_tab()`. After `Ctrl+S` / Save As, keep `mode="text"`.
- New window actions (not the PPTX `actionTextPreview` / `actionVisualPreview` shortcuts):
  - `actionMarkdownEdit`: `Ctrl+I`, `ApplicationShortcut`, calls restore-text with `editable=True`
  - `actionMarkdownPreview`: `Ctrl+T`, `ApplicationShortcut`, force-saves then `_restart_preview(..., "visual")`
- Enable those actions only when the current tab is Markdown. PPTX keeps existing hidden actions without these shortcuts.
- `_ensure_markdown_saved() -> bool`: if the text view has no path or is dirty, run `save_current_tab()`; return False if still no path or still dirty (Save As cancelled). Then switch.
- `_restore_markdown_text(..., *, editable: bool = True)` for Ctrl+I.

## 4. Testing

- Open existing `.md` → `mode == "visual"`; preview_fn called with `"visual"`; no `MarkdownTextView`.
- Untitled `+` → `MarkdownTextView` editable; save keeps text mode.
- Ctrl+I on visual `.md` → editable `MarkdownTextView`.
- Dirty Ctrl+T → file written, then visual.
- Untitled Ctrl+T with cancelled Save As → still editor.
- Ctrl+I / Ctrl+T are no-ops on PPTX.
- Caption-move and min/max click tests stay green.
