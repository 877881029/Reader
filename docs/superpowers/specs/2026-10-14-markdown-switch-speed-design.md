# Markdown Edit/Preview Switch: No Welcome Flash, Fast Return Design

Status: Implemented
Progress ledger: `docs/STATUS.md`

## Problem (reproduced)

New Markdown draft (`+` → 新建文件), type, switch 编辑 → 预览 → 编辑 → 预览:

| switch | total | welcome page shown |
|---|---|---|
| first edit→preview | 3.6 s | 1.7 s → 3.6 s |
| preview→edit | 0.1 s | no |
| second edit→preview | 1.8 s | 0.2 s → 1.8 s |

Root causes:

1. **Welcome fallback**: `_install_document_content` disposes the editor as soon
   as the new `MarkdownVisualView` is installed, but the view stays hidden until
   its page reports ready. The tab then has no visible content and, because the
   window started from the welcome page (`_welcome_allowed`),
   `_refresh_content_stack` shows the welcome page.
2. **Delay**: every switch creates a new `MarkdownVisualView` (new
   QWebEngineView + profile → new Chromium renderer process). Measured on this
   machine: a fresh view needs ~1.2–1.4 s even for a tiny page (process spawn,
   slowed by endpoint security scanning `QtWebEngineProcess`), while reloading
   an existing view takes 0.17–0.4 s. The first switch also pays WebEngine
   start-up when warm-up has not finished.

## Fix

1. **Swap on ready**: when installed content is not ready yet, keep the
   currently visible content in place (marked retiring, editor made read-only)
   and remove it only when the new content reports ready or falls back
   (`_mark_preview_ready`). Any later install or tab close disposes it as before.
2. **Reuse the preview view**: switching preview → edit parks the ready
   `MarkdownVisualView` hidden on the page (out of the layout, events unbound).
   Switching back to preview, after the save step, reinstalls the parked view and
   calls a new `MarkdownVisualView.reload()` (same page/process, re-fetches the
   saved file, emits `ready` again) instead of running a new preview request.
   The parked view is discarded when its source path differs from the document
   (Save As), when it is in fallback/shutdown, and on tab/window close.

## Acceptance

- During a switch the welcome page is never shown and the editor stays visible
  (read-only) until the preview is ready.
- Second and later edit → preview switches reuse the same view object and show
  the edited content.
- Parked views are shut down on tab close; stale parked views are not reused.
- Real-window measurement: later switches ≤ ~0.6 s, zero welcome frames.