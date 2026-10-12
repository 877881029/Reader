# Hex View Alignment and Adaptive Layout Implementation Plan

Status: Approved

**Spec:** `docs/superpowers/specs/2026-10-12-hex-layout-design.md`

## Task 1: Exact per-cell geometry

**RED** rendered highlight edges are background and contain glyph ink for
every byte; hover in gaps maps to the nearest unit; centre round-trip.
**GREEN** float metrics, per-cell drawing, gap-inclusive hit testing, half gap.

## Task 2: Adaptive font, centring and zoom

**RED** font grows with width to the cap, then the block is centred; minimum
size scrolls; Ctrl+wheel / Ctrl+= / Ctrl+- / Ctrl+0 behaviour.
**GREEN** fit computation on resize, manual override.

## Task 3: Docs, release gate, install