# Markdown Edit + Chrome Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or subagent-driven-development) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix title-bar dragging, shrink default height to 640px, make Markdown Notepad-like (fast open → click to edit → Ctrl+S), default new tabs to untitled `.md`, and warm WebEngine at startup.

**Architecture:** Expand `hit_test_for_window` so non-interactive chrome is `HTCAPTION`. Add `MarkdownTextView` for sync UTF-8 edit. Route default `.md` opens and `+`/new-window through that editor; keep visual MD as an explicit mode. Warm Chromium once after first show.

**Tech Stack:** Python 3.12+, PySide6 Widgets/WebEngine, pytest-qt.

## Global Constraints

- Default size `(1200, 640)`; keep width 1200.
- New window / `+` → untitled editable Markdown.
- Open `.md` → read-only fast text, click to edit; Ctrl+S save / Save As.
- Visual MD remains available via existing visual action.
- WebEngine warmup must not block first paint.
- Commit + push each task; update `docs/STATUS.md`.

---

## File Structure

- Create: `src/reader/preview/md_text_view.py` — `MarkdownTextView`
- Create: `src/reader/preview/webengine_warmup.py` — idempotent warmup
- Create: `tests/test_md_text_view.py`
- Create: `tests/test_webengine_warmup.py`
- Modify: `src/reader/shell/title_chrome.py` — caption hit-test
- Modify: `src/reader/shell/window.py` — size, save, new draft, md default editor
- Modify: `src/reader/app.py` / `src/reader/__main__.py` — warmup schedule; new window draft
- Modify: `tests/test_window.py`, `tests/test_title_chrome.py`
- Modify: `docs/STATUS.md`

---

### Task 1: Caption drag + default height

**Files:** `title_chrome.py`, `window.py`, `tests/test_window.py`, `tests/test_title_chrome.py`

- [x] **Step 1: Failing tests**
- [x] **Step 2: RED**
- [x] **Step 3: Implement hit-test + `DEFAULT_SIZE = (1200, 640)` / lower minimum height to `(800, 400)`**
- [x] **Step 4: GREEN + commit/push** (`39f27f4`)

---

### Task 2: MarkdownTextView + save

**Files:** create `md_text_view.py`, `tests/test_md_text_view.py`; wire `window.py`

- [x] **Step 1: Failing unit tests** for load read-only, click enables edit, dirty `*`, save/save_as UTF-8
- [x] **Step 2: Implement `MarkdownTextView`**
- [x] **Step 3: Window loads `.md` via text view by default; `actionSave` Ctrl+S; visual action still works**
- [x] **Step 4: GREEN focused tests + commit/push**

---

### Task 3: New window / + untitled draft

**Files:** `window.py`, `app.py`/`__main__.py`, tests

- [x] New window with no files → one untitled MD draft (editable)
- [x] `+` adds another untitled draft
- [x] Empty-window hint only when zero tabs (after closing all)
- [x] Commit/push

---

### Task 4: WebEngine warmup

**Files:** `webengine_warmup.py`, `app.py`, tests

- [x] `warmup_webengine(app)` creates hidden profile/page, processes events, disposes; second call no-op
- [x] Schedule via `QTimer.singleShot(0, ...)` after first window
- [x] Commit/push

---

### Task 5: Full regression + frozen certify

- [x] `pytest` full (`321 passed, 1 skipped`)
- [ ] `build_windows.ps1` + `smoke_windows.ps1`
- [ ] Refresh desktop shortcut
- [ ] STATUS complete + push

## Spec coverage

| Requirement | Task |
|---|---|
| Caption drag | 1 |
| Height -20% | 1 |
| MD fast open + click edit + Ctrl+S | 2 |
| New window / + untitled.md | 3 |
| WebEngine warmup | 4 |
| Frozen certify | 5 |
