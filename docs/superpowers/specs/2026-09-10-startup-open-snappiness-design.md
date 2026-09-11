# Startup and Open Snappiness

Date: 2026-09-10  
Status: Approved by user (fix 3–4s blank launch, open-file flash, intermittent long render; implement without extra gates)  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Cold-start from the desktop shortcut must show the paper welcome chrome (icon + UI) without a multi-second blank desktop. Opening a file from that welcome page must not look like the window closed and reopened. First document paint must not occasionally stall for a long time.

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.

## 2. Symptoms and causes

| Symptom | Cause |
|---|---|
| 3–4s with no window after double-click | `register_open_with` / `create_desktop_shortcut` run after `show()` but **before** `qapp.exec()`, so the first paint cannot happen. `schedule_webengine_warmup(..., delay_ms=0)` then immediately constructs Chromium and calls `processEvents()`, stealing the first frames. |
| Open file looks like close + reopen | Welcome stack is swapped for an empty “正在加载…” pane, then the first `QWebEngineView` creates a native Chromium HWND (warmup currently builds a page, **deletes** it, and shuts Chromium back down). |
| Occasional long render | Same Chromium cold start on first visual/PDF/HTML view. Warmup does not keep a process alive, so Defender/disk can make the next profile creation stall. |

## 3. Decisions

1. Enter the Qt event loop immediately after `show()`. Shell integration runs on `QTimer.singleShot(0, ...)`.
2. Enable `AA_ShareOpenGLContexts` before `QApplication`.
3. Apply native icons / DWM frame styles from `MainWindow` construction (`winId()` before `show`) so the first visible frame already has the R icon.
4. WebEngine warmup: delayed (~400ms) after first window, constructs a **hidden kept-alive** `QWebEngineView` (no `processEvents()`), skipped when `READER_SKIP_WEBENGINE_WARMUP` is truthy (pytest).
5. Keep the welcome page as the stack current widget until a tab has real preview content (not only the loading label), **when the user already saw welcome** (empty launch, then Open / drop / recent). Tab chrome can show the new tab immediately.
6. When installing preview content, add the viewer before disposing the loading label so the pane is never empty.
7. Cold-start **with files** (Explorer double-click / argv): do **not** `show()` the welcome page first. Create the window hidden, `open_paths`, then `show()` on the tabs stack (loading label is OK). Welcome must not appear as a frame that then “closes”.

## 4. Non-goals

- Splash executable / stub loader in front of PyInstaller.
- Sharing one `QWebEngineProfile` across documents (interceptors stay per-view).
- Restyling Chromium PDF chrome.
- Changing drag / caption hit testing.

## 5. Testing

- Launch: shell integration is scheduled, not run before `exec()`.
- Warmup: first call keeps a hidden view; second call is a no-op; reset disposes it; `processEvents` is not required for the keep-alive.
- Window: while a preview worker is blocked, content stack stays on welcome; after content is installed, stack shows tabs.
- Caption-move and min/max hit tests stay green.
- Frozen smoke PPTX / MD / IPC still pass.
