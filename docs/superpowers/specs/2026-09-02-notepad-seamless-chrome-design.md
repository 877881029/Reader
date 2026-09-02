# Notepad Seamless Chrome Design

Date: 2026-09-02  
Status: Approved by user (continuous execute; screenshots attached)  
Depends on: `docs/superpowers/specs/2026-09-01-notepad-titlebar-design.md`  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Fix two remaining gaps versus Windows 11 Notepad:

1. **Window still cannot be moved** by dragging the title/tab chrome.
2. **Chrome and editor look like two stacked panels**: gray tab strip, a hard middle divider, and a bottom status bar (`文本编辑`).

## 2. Problem

Hit-test unit tests map chrome empty space to `HTCAPTION`, but the live window does not move. Root cause: Qt frameless + restored `WS_CAPTION` often swallows `WM_NCHITTEST`; the empty `titleCaption` widget never calls `QWindow.startSystemMove()`. Users dragging the gray strip get a client mouse press that does nothing.

Visually, `TitleChrome` uses `#f3f3f3` plus `border-bottom`, `QTabWidget::pane` keeps a frame, `QPlainTextEdit` keeps a sunken border, and `QStatusBar` stays visible. That is the seam in the user’s Reader screenshot.

## 3. Non-goals

- Do not add Notepad’s File / Edit / View row or the markdown formatting / Copilot / settings toolbar (the extra strip in the third screenshot).
- Do not restore a visible Preview menu.
- Do not change Markdown save/open behavior, PPTX visual, IPC, or packaging layout.
- Do not drop Win32 `WS_CAPTION|THICKFRAME` (taskbar min/restore still required).

## 4. Approved decisions

| Topic | Choice |
|---|---|
| Drag | Caption / icon / empty chrome: `windowHandle().startSystemMove()` on left press; Win32 `WM_NCLBUTTONDOWN/HTCAPTION` fallback. Keep `WM_NCHITTEST` for edges and Snap Layouts. |
| Tab + editor color | Same surface `#ffffff`; selected tab blends into the page; unselected tabs are light pills. |
| Middle divider | None: no chrome bottom border, no tab pane frame, no editor frame. |
| Status bar | Hidden. `status_text()` / `show_status()` stay as in-memory API for tests and errors; nothing painted at the bottom. |
| Double-click caption | Maximize / restore (existing behavior). |

## 5. Architecture

### 5.1 Drag

`TitleChrome` treats icon, empty padding, and `titleCaption` as move handles. Interactive children stay client: tab bar, `+`, min/max/close.

On left press of a move handle:

1. Call `window.windowHandle().startSystemMove()` when a `QWindow` exists.
2. If that returns false on Windows, `ReleaseCapture` + `SendMessage(WM_NCLBUTTONDOWN, HTCAPTION)`.

`nativeEvent` hit-testing remains for resize borders and `HTMAXBUTTON`. Convert `WM_NCHITTEST` lParam from physical pixels with the screen `devicePixelRatio` so DPI scaling does not map caption points into the editor.

### 5.2 Seamless surface

- Chrome, content stack, tab pane, and markdown editor share `#ffffff`.
- Remove `border-bottom` on `titleChrome`.
- `QTabWidget::pane { border: none; margin: 0; }`
- `QPlainTextEdit#markdownTextEditor` uses `NoFrame` and no border.

### 5.3 Status bar

`QStatusBar` is created (Qt `QMainWindow` expects one) but hidden (`visible=False`, height 0, no size grip). Messages still go through `show_status` / `status_text()`.

## 6. Testing

- Left-press on `titleCaption` / `titleAppIcon` calls `startSystemMove` (monkeypatched `QWindow`).
- Left-press on `tabNewButton` / tab close does **not** start a move.
- Status bar widget is not visible and has height 0; `status_text()` still updates.
- Chrome and markdown editor report the same background color; chrome has no bottom border; tab pane and editor have no frame.
- Existing hit-test, tab, IPC, and packaging tests stay green.
- Frozen smoke + desktop shortcut after implementation.

## 7. Process

Commit and push at spec, plan, and task boundaries per `docs/STATUS.md`.
