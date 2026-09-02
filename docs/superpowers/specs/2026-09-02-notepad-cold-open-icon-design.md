# Notepad Cold-Open Flush and Taskbar Icon Design

Date: 2026-09-02  
Status: Approved by user (continuous execute; drag/buttons must stay working)  
Depends on: `docs/superpowers/specs/2026-09-02-notepad-spacing-surface-design.md`  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Two remaining Notepad-chrome bugs after spacing/surface polish:

1. **Cold open first-line gap.** Direct launch still leaves ~30px empty space above the first line. Maximize then restore snaps the editor flush under the title strip. Zoom of the editor is not involved — this is window maximize/restore.
2. **Taskbar icon.** The desktop taskbar button shows a tiny window thumbnail instead of the blue **R** from `assets/icons/reader.ico`. The in-window title icon can still be correct.

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.

## 2. Root cause

**Gap.** `ChromeTabWidget` reparents the tab bar into `TitleChrome`, then stretches `qt_tabwidget_stackedwidget` to `(0,0,w,h)` in `showEvent`/`resizeEvent`. After first show, `MainWindow.showEvent` restores `WS_CAPTION|WS_THICKFRAME|...` with `SWP_FRAMECHANGED`. That re-runs `QTabWidget` layout, which puts the stack back at `y≈30` (ghost tab-bar height). Maximize/restore fires `resizeEvent`, so the stretch sticks. The existing flush test hid this by calling `_stretch_pane()` after `waitExposed`.

**Taskbar icon.** `setWindowIcon` runs before the HWND is fully framed. `SetWindowLong` + `SWP_FRAMECHANGED` re-registers the window with the shell. Explorer then uses a DWM snapshot for the taskbar button unless `WM_SETICON` (`ICON_SMALL` / `ICON_BIG`) is applied **after** the frame styles.

## 3. Architecture

- Stretch the tab stack after every `QEvent.LayoutRequest`, after Win32 frame restore, and once on the next event-loop tick (`QTimer.singleShot(0, ...)`). Skip `setGeometry` when the stack already matches `self.rect()`.
- After `_ensure_win32_frame_styles`, `LoadImageW` the `.ico` and `SendMessageW(WM_SETICON)` for small and big icons. Keep the loaded `HICON`s on the window. Do not set class-long icons (`GCLP_HICON`) — that would affect every Qt window in the process.
- Flush test must measure after show **without** a manual `_stretch_pane()` call.
- Icon test: clear HWND icons, call `_ensure_win32_frame_styles()`, assert `WM_GETICON` is non-zero again.

## 4. Testing

- Untitled editor top within 12px of chrome bottom after `show` + `waitExposed` (no manual stretch).
- After clearing `WM_SETICON`, restoring frame styles puts a non-zero small/big icon back on the HWND.
- Existing caption-move and min/max click tests stay green.
