# Plan: UI Font Faster First Paint

Date: 2026-10-15
Status: Implemented (2026-10-15)
Spec: `docs/superpowers/specs/2026-10-15-ui-font-fast-start-design.md`

## Task 1: Font coverage tests and fix
RED: GDI glyph-coverage helper in tests; app font is Microsoft YaHei UI; every
window/Browser text exists in its widget's primary font. GREEN: theme constants,
`ReaderApp` sets the app font, welcome stack, Segoe UI Symbol for caption and
Browser buttons.

## Task 2: Measure, docs, release, install
Dev and frozen cold-start measurement; README / 功能全解 note if needed; release
gate; install; STATUS with SHA; mark spec and plan Implemented.
