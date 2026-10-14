# Markdown Edit/Preview Switch Implementation Plan

Status: Approved

**Spec:** `docs/superpowers/specs/2026-10-14-markdown-switch-speed-design.md`

## Task 1: Swap on ready (no welcome flash)
RED window test with a fake visual view that stays not-ready: editor remains
visible/read-only, content stack never shows welcome, editor removed after ready.
GREEN `_install_document_content` + `_mark_preview_ready`.

## Task 2: Reuse parked preview view
RED md_view test for `reload()` (re-fetch + second ready) and window tests
(same object reused, stale path not reused, parked view shut down on close).
GREEN `MarkdownVisualView.reload`, parking in `_restore_markdown_text`, reuse in
`switch_current_tab_to_visual`, disposal.

## Task 3: Measure, release gate, install, docs