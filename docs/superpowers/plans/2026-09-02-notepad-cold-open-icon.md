# Notepad Cold-Open Flush and Taskbar Icon Plan

> **For agentic workers:** Use superpowers:executing-plans. User asked to fix both bugs in this session — execute inline without review gates.

**Goal:** Cold-open editor flush under the title strip; taskbar button uses the blue R icon.

**Architecture:** Re-stretch the reparented `QTabWidget` stack after layout and Win32 frame restore. Re-apply `WM_SETICON` from `reader.ico` after `SetWindowLong`/`SWP_FRAMECHANGED`.

**Tech Stack:** PySide6, Win32 `user32`, pytest-qt.

## Global Constraints

- Do not edit `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- Do not set `GCLP_HICON` / `GCLP_HICONSM` (process-wide Qt class icons).
- Commit + push; update `docs/STATUS.md`.

---

### Task 1: Cold-open flush + HWND icons

**Files:**
- Modify: `tests/test_window.py` (`test_untitled_editor_starts_flush_under_title_chrome` and a new icon test)
- Modify: `src/reader/shell/window.py` (`ChromeTabWidget`, `MainWindow.showEvent`, `_ensure_win32_frame_styles`)

**Interfaces:**
- Consumes: existing `ChromeTabWidget._stretch_pane()`, `_ensure_win32_frame_styles()`, `_window_icon_path()`
- Produces: layout-driven pane stretch; `_apply_native_window_icons(hwnd: int) -> None`

- [ ] **Step 1: Write the failing tests**

Change the flush test so it does **not** call `_stretch_pane()`. After show, wait until the editor is flush (or time out):

```python
def test_untitled_editor_starts_flush_under_title_chrome(qtbot):
    from reader.preview.md_text_view import MarkdownTextView

    window = make_window(lambda _path, office=None, mode="builtin": builtin_result())
    qtbot.addWidget(window)
    window.add_untitled_markdown_tab()
    window.show()
    qtbot.waitExposed(window)

    def gap() -> int:
        chrome = window.findChild(QWidget, "titleChrome")
        view = window.findChild(MarkdownTextView)
        assert chrome is not None and view is not None
        chrome_bottom = chrome.mapTo(window, QPoint(0, chrome.height())).y()
        editor_top = view._editor.mapTo(window, QPoint(0, 0)).y()
        return editor_top - chrome_bottom

    qtbot.waitUntil(lambda: 0 <= gap() <= 12, timeout=1000)
```

Add:

```python
@pytest.mark.skipif(platform.system() != "Windows", reason="Win32 HWND icons")
def test_win32_frame_styles_restore_hwnd_icons(qtbot):
    import ctypes

    window = make_window(lambda _path, office=None, mode="builtin": builtin_result())
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    hwnd = int(window.winId())
    user32 = ctypes.windll.user32
    wm_seticon, wm_geticon = 0x0080, 0x007F
    user32.SendMessageW(hwnd, wm_seticon, 0, 0)
    user32.SendMessageW(hwnd, wm_seticon, 1, 0)
    assert user32.SendMessageW(hwnd, wm_geticon, 0, 0) == 0
    window._ensure_win32_frame_styles()
    assert user32.SendMessageW(hwnd, wm_geticon, 0, 0) != 0
    assert user32.SendMessageW(hwnd, wm_geticon, 1, 0) != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_window.py::test_untitled_editor_starts_flush_under_title_chrome tests/test_window.py::test_win32_frame_styles_restore_hwnd_icons -v`

Expected: flush test times out or asserts gap > 12 (stack still at `y≈30`); icon test asserts GETICON still 0 after `_ensure_win32_frame_styles()`.

- [ ] **Step 3: Minimal implementation**

`ChromeTabWidget`: stretch on `LayoutRequest` / resize / show / `tabInserted`; `QTimer.singleShot(0, self._stretch_pane)` from `showEvent`; skip `setGeometry` when already matching `self.rect()`.

`MainWindow`: store `_icon_path`; after `_ensure_win32_frame_styles()` stretch the pane; `_apply_native_window_icons` uses `LoadImageW` + `SendMessageW(WM_SETICON)` with proper 64-bit `WPARAM`/`LPARAM` ctypes types.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_window.py::test_untitled_editor_starts_flush_under_title_chrome tests/test_window.py::test_win32_frame_styles_restore_hwnd_icons tests/test_window.py::test_window_buttons_are_client_hits_and_clickable tests/test_title_chrome.py -v`

Expected: PASS. Drag/button tests still green.

- [ ] **Step 5: Commit**

```text
fix: stretch editor pane after Win32 frame restore and reapply taskbar icons
```

---

### Task 2: Frozen certify

**Files:** `docs/STATUS.md`; `dist/Reader/Reader.exe` (build output)

- [ ] Full `python -m pytest`
- [ ] `scripts/build_windows.ps1` then `scripts/smoke_windows.ps1`
- [ ] Refresh desktop `Reader.lnk` with `overwrite=True`
- [ ] Update STATUS (current goal completed, next step = cold-open + taskbar icon manual check)
- [ ] Commit + push `origin/main`
