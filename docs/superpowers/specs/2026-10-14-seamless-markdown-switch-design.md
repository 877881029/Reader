# Seamless Markdown Edit/Preview Design

Status: Approved
Progress ledger: `docs/STATUS.md`

## Goal

Switching between 编辑 and 预览 should feel instant, like VS Code / Cursor /
Typora. User decision (2026-10-14): the preview shows the editor's current text;
switching never forces a save and never opens Save As for new files.

## How IDEs do it, applied here

1. **Both views stay alive.** Each Markdown tab keeps one editor
   (`MarkdownTextView`) and one preview (`MarkdownVisualView`). Switching takes
   one out of the page layout (kept hidden on the page) and puts the other in;
   no widget is recreated, so cursor, scroll, undo history and the renderer
   process survive.
2. **Live content push, no reload.** The preview no longer has to read the file:
   `MarkdownBridge` gains `hasLiveSource` / `liveSource` and a
   `liveSourceChanged(str)` signal. The page renders the live text at start-up
   (no fetch) and re-renders in place when it changes, keeping the scroll
   position. `MarkdownVisualView.set_source_text(text)` drives it and emits
   `rendered` after each re-render.
3. **Background updates.** While editing, edits are pushed to the hidden preview
   after a 150 ms pause; switching flushes any pending push first, so the preview
   is already current when shown.
4. **Pre-created preview.** When a Markdown tab enters edit mode without a
   preview (new file, or opened as text), a preview is created in the background
   after 300 ms with the current text; the first switch is then instant. If the
   user switches before it is ready, the editor stays visible until it is
   (existing swap-on-ready rule).

## Details

- Preview source path: the document path for saved files; for untitled drafts a
  non-existent path in `%TEMP%\reader-untitled\` (keeps the offline interceptor
  scoped to an empty folder). A preview whose source path no longer matches
  (Save As) is discarded and re-created.
- Fallback HTML for live previews comes from the same text
  (`fmt_md.to_visual_text`).
- The kept editor remains the document's editable view: `*` title, Ctrl+S /
  Ctrl+Shift+S and the unsaved-changes prompt work in preview mode. Replace
  (Ctrl+H) only acts while the editor is visible.
- Kept widgets are disposed with the tab/window.
- Removed: forced save before preview, `_ensure_markdown_saved`, and the
  file-reload reuse path (`MarkdownVisualView.reload`).

## Acceptance

- Edit → preview and preview → edit both under 100 ms once the preview exists;
  the preview shows unsaved text; no Save As dialog; no welcome page.
- Cursor position and undo history survive a round trip.
- Closing a tab with unsaved changes from preview mode still prompts.