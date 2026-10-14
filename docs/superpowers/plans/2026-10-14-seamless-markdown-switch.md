# Seamless Markdown Edit/Preview Implementation Plan

Status: Implemented

**Spec:** `docs/superpowers/specs/2026-10-14-seamless-markdown-switch-design.md`

## Task 1: Live source in the md-viewer page
RED vitest (`main.test.ts`): live source used without fetch; `liveSourceChanged`
re-renders, keeps scroll, signals ready again. GREEN `main.ts`; rebuild bundle.

## Task 2: Live source in MarkdownVisualView
RED pytest (md_view + real WebEngine): untitled non-existent source renders
pushed text; second push re-renders in the same page and emits `rendered`;
`fmt_md.to_visual_text`. GREEN bridge properties/signal, `set_source_text`,
`rendered`, drop `reload`.

## Task 3: Window keeps both views, pushes live, pre-creates preview, no save
RED window tests (no save/dialog, instant round trip with same widgets,
cursor/undo kept, background push debounce, pre-created preview, close prompt
in preview mode, Save As discards stale preview). GREEN window changes; update
superseded tests.

## Task 4: Measure, docs, release gate, install