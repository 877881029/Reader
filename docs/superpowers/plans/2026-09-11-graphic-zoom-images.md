# Graphic Zoom and Raster Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Hidden Ctrl+wheel zoom on graphic tabs, plus PNG/JPEG/GIF/WebP/BMP preview.

**Architecture:** Shared `GraphicView` canvas (fit × user zoom, drag pan). SVG and raster subclasses. Same sniff/pipeline pattern as SVG.

**Tech Stack:** PySide6 QtGui/QtSvg, pytest-qt.

## Global Constraints

- Do not change `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- No on-screen zoom controls on graphic tabs.
- User asked to implement without extra approval gates.

---

### Task 1: Zoom + images

- [x] Failing tests for Ctrl+wheel zoom (no chrome) and raster suffixes
- [x] `graphic_view.py`, `image_view.py`, `formats/image.py`
- [x] Wire sniff, associate, pipeline, cache skip, dialog, welcome, README, 功能全解

### Task 2: Freeze

- [x] Full pytest; freeze; smoke; desktop shortcut; STATUS; push `origin/main`
