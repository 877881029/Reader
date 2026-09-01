# Notepad-Style Title Bar Design

Date: 2026-09-01  
Status: Implemented (Approach A)
Depends on: `docs/superpowers/specs/2026-08-24-reader-ux-packaging-design.md`  
Progress ledger: `docs/STATUS.md`

This increment supersedes the visible **文件 / 预览** menu bar, the tab-corner **打开** button, and the blank-tab hint that says `文件 → 打开`. Default preview policy (builtin-first, optional Office/text/visual) does not change.

## 1. Goal

Make Reader’s chrome match Windows 11 Notepad’s single-row header:

1. One row: app icon, open tabs, **+**, caption drag region, minimize / maximize / close.
2. Remove the extra “property” row (the `QMenuBar` showing 文件 / 预览 and the right-side **打开** tool button).
3. **+** sits immediately after the last visible tab and always creates a blank `未命名` tab.
4. Preserve native Windows window behavior: move, edge/corner resize, double-click maximize/restore, and Snap Layouts on the maximize button.

## 2. Problem (current)

`MainWindow` uses the system title bar, then a `QMenuBar`, then a `QTabWidget` with a **TopRightCorner** widget (`打开` + `+`). That is three chrome bands. The screenshot gap versus Notepad is layout, not missing open/preview logic.

## 3. Non-goals

- Do not add an icon overflow / “…” menu or restore 文件 / 预览 as visible chrome in this increment.
- Do not change PPTX/Markdown visual viewers, IPC, packaging, or file associations.
- Do not hide the bottom status bar (preview status still belongs there).
- Do not remember window size; default remains 1200×800, minimum 800×500.
- Do not implement a macOS/Linux custom title bar.

## 4. Approved decisions

| Topic | Choice |
|---|---|
| Layout | Approach A: frameless window + custom single-row chrome |
| Native behavior | Full: drag, resize, double-click caption, Win11 Snap Layouts on maximize |
| **+** | Always visible after the last tab; click adds a blank tab |
| Menus | No visible menu bar; `Ctrl+O`, drag-drop, Explorer “Open with” remain |
| Preview switching | Keep existing `QAction`s (`actionOfficePreview` etc.) for tests and later UI; do not show a Preview menu now |
| Blank hint | `拖入文件，或按 Ctrl+O 打开` |

## 5. Architecture

```text
MainWindow (FramelessWindowHint)
  TitleChrome  [icon][QTabBar...][+][caption stretch][min][max][close]
  QStackedWidget / existing tab pages
  QStatusBar
```

- Implement hit-testing in `nativeEvent` for `WM_NCHITTEST` (and `WM_NCCALCSIZE` as required so the frame still resizes). Map regions to `HTCAPTION`, `HTCLIENT`, `HTLEFT`/`HTRIGHT`/`HTTOP`/`HTBOTTOM` and corners, plus `HTMINBUTTON`, `HTMAXBUTTON`, `HTCLOSE`.
- Maximize-button hover must return `HTMAXBUTTON` so Windows 11 Snap Layouts appear.
- Icon, tabs, **+**, and the three window buttons are `HTCLIENT` (Qt handles clicks). Empty stretch between **+** and window buttons is `HTCAPTION` (drag / double-click maximize).
- Keep `actionOpen` (`Ctrl+O`) and `actionNewTab` as window actions even with no menu.
- Preview actions stay on the window object so existing `switch_current_tab_to_*` tests keep working; they are not placed in a visible menu.
- Do not use `QTabWidget.setCornerWidget` for Open/+.

Window icon in the chrome is the existing Reader R (`windowIcon()` / `assets/icons`).

## 6. Interaction

- **+**: `add_blank_tab()`; title `未命名`; same drop-replace behavior as today.
- Tab close **×**: unchanged `close_tab`.
- Last tab closed: empty window, no leftover blank (existing rule).
- Too many tabs: tab bar scrolls; **+** remains immediately after the last *visible* tab cluster (Notepad-like), not in the far right corner.
- Caption double-click: maximize/restore.
- Edge drag: resize. Buttons: minimize, maximize/restore, close (`WA_DeleteOnClose` unchanged).
- `Ctrl+O`: same native multi-select dialog and filters.
- Drag-drop onto chrome or content: unchanged path open rules.

## 7. Visual

- Light chrome, compact 32–36 px row, no second menu strip.
- Selected tab is a light rounded pill (Notepad-like), not a separate toolbar.
- Window buttons use standard caption metrics and hover states; close hover is destructive red.
- Content area starts immediately under the chrome.

## 8. Error handling

| Case | Behavior |
|---|---|
| `nativeEvent` unavailable in tests | Widget clicks and shortcuts still work; hit-test unit tests feed synthetic `WM_NCHITTEST` |
| High-DPI / mixed DPI | Hit rectangles use device pixels consistent with `WM_NCHITTEST` lParam |
| Maximized | Resize borders disabled; restore via maximize button or caption double-click |

## 9. Testing (TDD)

- Menu bar is hidden / height 0; no widget named `tabOpenButton`.
- `tabNewButton` exists, is enabled, and sits after the last tab (not in a right-corner Open/+ cluster).
- Click **+** / `actionNewTab` still adds `未命名`; hint text is `拖入文件，或按 Ctrl+O 打开`.
- `actionOpen` shortcut remains `QKeySequence.Open`; triggering it still opens the dialog (existing monkeypatch tests).
- Preview `QAction`s still enable/disable per current tab; no visible Preview menu.
- Synthetic `WM_NCHITTEST`: caption stretch → `HTCAPTION`; maximize button → `HTMAXBUTTON`; content → `HTCLIENT`; left edge → `HTLEFT`.
- Existing tab/open/close/IPC/Office tests remain green.
- Frozen smoke still passes; rebuild `Reader.exe` and refresh the desktop shortcut.

## 10. Process requirement

Implementation must follow `docs/STATUS.md` and `.cursor/rules/git-progress-handoff.mdc`: commit and push at spec, plan, and task boundaries.
