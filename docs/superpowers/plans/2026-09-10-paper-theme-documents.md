# Paper Theme Across Documents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Carry the welcome-page paper palette into every open document surface so `.md` / `.docx` / `.pptx` / `.xlsx` / `.pdf` no longer snap to notepad gray or a dark PPTX shell.

**Architecture:** One token module (`reader.theme`) feeds Qt chrome, HTML wrappers, and the md/pptx viewer CSS. Slide canvases and PDF page pixels stay authored white.

**Tech Stack:** PySide6, QWebEngine, Vite md-viewer / pptx-viewer bundles, pytest, `scripts/build_windows.ps1`.

## Global Constraints

- Do not change `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- Tokens: PAPER `#f4efe6`, CHROME `#ebe4d8`, INK `#1c1915`, MUTED `#8a8176`, COBALT `#2563eb`, CARD `#fffaf2`, LINE `#e4d9c7`.
- PDF: only WebEngine page background; do not restyle Chromium PDF viewer chrome.
- PPTX: rail/toolbar/stage paper; `.viewer-shell__host` stays `background: white`.

---

### Task 1: Tokens, wrap helper, chrome, and HTML previews

**Files:**
- Create: `src/reader/theme.py`, `tests/test_theme.py`
- Modify: `src/reader/shell/window.py`, `title_chrome.py`, `welcome.py`, `preview/md_text_view.py`, `formats/{md,docx,xlsx,pptx}.py`, matching tests

- [x] Token file and `wrap_document_html()` emit PAPER / COBALT
- [x] Root, tabs, title chrome, markdown editor use tokens
- [x] Format HTML uses wrap helper
- [x] Caption-move and min/max hit tests stay green

### Task 2: Visual viewer CSS + committed hashed bundles

**Files:**
- Modify: `web/md-viewer/src/style.css`, `web/pptx-viewer/src/style.css`, `preview/md_view.py`, `preview/pptx_view.py`, `assets/md-viewer/**`, `assets/pptx-viewer/**`

- [x] Source CSS uses paper tokens; PPTX no longer `#0f172a`
- [x] WebEngine page background PAPER
- [x] Rebuild hashed bundles so frozen exe matches source

### Task 3: Freeze, smoke, desktop shortcut

- [x] Full pytest
- [x] `scripts/build_windows.ps1` (stop `Reader.exe` first)
- [x] `scripts/smoke_windows.ps1 -ReaderExe dist\Reader\Reader.exe -TimeoutSeconds 90`
- [x] `create_desktop_shortcut(..., overwrite=True)`
- [x] Update `docs/STATUS.md` with exe size/SHA256
