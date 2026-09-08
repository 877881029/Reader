# Empty Launch Welcome Page Design

Date: 2026-09-08  
Status: Approved by user (option A; implement first, iterate after)  
Depends on: Notepad chrome, `VERSION` 0.1.0, existing empty `contentStack`  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Double-clicking the desktop icon opens a **zero-tab** window. The content area is a welcome page (recent files + version), not an untitled Markdown tab. `+` still creates `未命名.md`. Taskbar small/big icons are the blue R after show, not a live window thumbnail.

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.

## 2. Current behavior

- Empty argv calls `add_untitled_markdown_tab()`, so launch looks like an open empty file.
- Zero-tab stack page is a single centered hint label `emptyWindowHint`.
- `WM_SETICON` runs inside `_ensure_win32_frame_styles` during `showEvent`, but is not reapplied on the next event-loop tick. Explorer can still snapshot the window for the taskbar button.

## 3. Architecture

- `__main__.main`: if no file args, do **not** create a draft tab.
- Replace the empty stack page with `WelcomePage`: title Reader, version from `VERSION` via `resource_path`, Open / New Markdown buttons, keep `emptyWindowHint` (Ctrl+O / drop), recent list.
- Persist recents in `%LOCALAPPDATA%\Reader\recent.json` (max 12, most recent first). Record on `decide_open` `to_open` and after Markdown save-as to a real path. Skip `未命名-*.md`. Drop missing files when rendering the list.
- `+` / `actionNewTab` still call `add_untitled_markdown_tab()`.
- After frame restore, `QTimer.singleShot(0, ...)` reapplies `WM_SETICON` small+big.
- Collect `VERSION` in `reader.spec` for frozen runs.

## 4. Non-goals

- VS Code Welcome **tab**, walkthroughs, Open Folder, Git clone.
- Changing drag/window-control hit testing.
- Committing binaries.

## 5. Testing

- Empty `main(["Reader.exe"])` does not call `add_untitled_markdown_tab`.
- New `MainWindow` has 0 tabs, visible version + recent list + `emptyWindowHint`.
- `+` still adds untitled Markdown.
- Opening a real file prepends it to recents; missing paths omitted from the list.
- After clearing HWND icons, show + processEvents restores non-zero `WM_GETICON`.
- Caption-move and min/max click tests stay green.

## 6. Follow-up (2026-09-08, user screenshot)

Keep the two-column layout. Polish the welcome surface (paper field, filled primary action, recent rows as slips). Taskbar still showed a live DWM snapshot of the white page even though `WM_GETICON` was non-zero — set `DWMWA_FORCE_ICONIC_REPRESENTATION` and HWND `AppUserModelID` / `RelaunchIconResource`. Do not change `nativeEvent`.

