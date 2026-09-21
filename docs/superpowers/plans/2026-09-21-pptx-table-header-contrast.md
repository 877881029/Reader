# PPTX Table Header Contrast Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Do not change `hit_test_local` / `begin_window_move` / `nativeEvent`.

**Goal:** Table header labels with white/cyan text on a dark fill must stay visible in Reader.

**Root cause:** `pptx-viewer@0.2.2` interpolates `font-family: "${name}"` into an HTML `style="..."` string, so the color declaration is parsed as a broken attribute.

## Task 1: Patch + tests

- [x] Synthetic fixture: Calibri, bold white header on `#0B1F3A`
- [x] Failing vitest: rendered header span `style.color` is white
- [x] Failing patch test for the CSS-quote replacement
- [x] Extend `patch-pptx-viewer.mjs`; rebuild `assets/pptx-viewer`
- [x] Tests pass

## Task 2: Docs, freeze, push

- [x] STATUS + 功能全解 note if needed
- [x] Full pytest; freeze; smoke; shortcut; push `origin/main`
