# Notepad-Like Markdown Edit & Chrome Polish Design

Date: 2026-09-01  
Status: Approved by user (Approach A); implementing  
Depends on: `docs/superpowers/specs/2026-09-01-notepad-titlebar-design.md`  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Polish Reader chrome and make Markdown text feel Notepad-like:

1. Drag the window from the title-bar chrome (not only a thin caption strip).
2. Default window height shrink ~20% (`1200×640`).
3. New window / `+` opens an untitled editable Markdown draft.
4. Opening `.md` shows text **fast** (read-only), becomes editable on click; Ctrl+S saves (Save As if untitled).
5. Warm up WebEngine at startup so the first PPTX/optional MD visual open is much closer to the second.

## 2. Approved decisions

| Topic | Choice |
|---|---|
| New document | Editable Markdown draft (`未命名.md`), not `.txt` |
| Save | Ctrl+S: overwrite if path exists; else native Save As (`.md`) |
| Open existing `.md` | Fast plain-text read-only view → click (or type) enables edit |
| Visual MD preview | Kept as optional `视觉模式`; not the default open path |
| First-open lag | Background WebEngine warmup for PPTX (+ MD visual when used) |
| Height | `DEFAULT_SIZE = (1200, 640)`; minimum height scaled down |

## 3. Non-goals

- Full rich WYSIWYG Markdown editor / live preview split.
- Making `.docx` / `.xlsx` / `.pptx` editable.
- Changing IPC, packaging layout, or file associations beyond `.md` open behavior.
- macOS/Linux custom chrome.

## 4. Architecture

### 4.1 Caption drag

`hit_test_for_window`:

1. Resize borders when not maximized (keep 8px).
2. Min / max / close → `HTMINBUTTON` / `HTMAXBUTTON` / `HTCLOSE`.
3. Tab bar and `tabNewButton` → `HTCLIENT`.
4. Any other point inside `titleChrome` → `HTCAPTION` (includes icon and empty stretch).
5. Else → `HTCLIENT`.

### 4.2 Markdown text editor

New `MarkdownTextView` (`QPlainTextEdit` wrapper):

- Loads UTF-8 (`errors="replace"`).
- Starts read-only for opened files; first click / key focus path enables edit.
- Untitled drafts start editable.
- Emits dirty state; tab title shows `*` when dirty.
- `save()` / `save_as()` write UTF-8; update path + clear dirty.

`MainWindow`:

- Default `.md` open uses text editor (sync read; no WebEngine).
- `actionVisualPreview` still switches current `.md` tab to visual WebEngine via existing pipeline.
- `actionTextPreview` / returning from visual restores text editor content from disk or buffer.
- `actionSave` (`Ctrl+S`) on current markdown text tab.

### 4.3 New window / `+`

- Replaces empty-hint-only startup: first window with no argv files opens one untitled MD draft.
- `+` / `actionNewTab` creates another untitled MD draft (not the old drop-hint blank tab).
- Dropping files onto an untitled empty draft can replace it (same replace-blank behavior).

### 4.4 WebEngine warmup

On primary `ReaderApp` start (after first window shown), schedule a one-shot idle warmup that constructs a hidden off-the-record `QWebEnginePage`/`Profile` (or loads a tiny `about:blank` view) then disposes it, so Chromium initializes before the first real visual document.

## 5. Testing

- Hit-test: point on chrome icon / caption stretch → `HTCAPTION`; on `+` → `HTCLIENT`; maximize → `HTMAXBUTTON`.
- Default size `(1200, 640)`.
- New window / `+` yields editable untitled markdown tab.
- Open `.md`: read-only until click; then editable; Ctrl+S Save As then overwrite.
- Existing PPTX visual + window regression suites stay green.
- Warmup helper is idempotent and does not open a visible window.
- Frozen smoke still passes; rebuild + desktop shortcut refresh.

## 6. Process

Commit/push at spec, plan, and task boundaries per `docs/STATUS.md`.
