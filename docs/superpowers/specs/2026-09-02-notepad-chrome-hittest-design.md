# Notepad Chrome Hit-Test Repair Design

Date: 2026-09-02  
Status: Approved by user (last retry; continuous execute)  
Depends on: `docs/superpowers/specs/2026-09-02-notepad-seamless-chrome-design.md`  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Make custom chrome behave like Windows 11 Notepad:

1. Min / max / close actually click.
2. Resize cursor and drag match the visible frame (not offset).
3. Window can be moved every time, not only once.
4. Title strip is Notepad gray; editor is white (distinct, not the same slab).

## 2. Root cause

Three mechanisms fought each other:

| Mechanism | Effect |
|---|---|
| `WM_NCHITTEST` → `HTMINBUTTON` / `HTMAXBUTTON` / `HTCLOSE` | Windows aims at native caption buttons that `WM_NCCALCSIZE` removed. Qt never gets the click. |
| `WM_NCHITTEST` → `HTCAPTION` plus `startSystemMove()` | First press reaches Qt and moves. Later presses stay non-client, so Qt never sees them and Windows also cannot drag a zero-height caption. |
| `lParam / devicePixelRatio` then `mapFromGlobal` | Mixes physical screen pixels with logical widget space. Right/bottom hit regions shift; the 8px fake frame eats the close button. |

## 3. Architecture

**One rule:** Qt-owned chrome is always `HTCLIENT`. Only a thin empty frame (not overlapping tabs, `+`, or window buttons) returns `HTLEFT` / `HTRIGHT` / `HTTOP` / `HTBOTTOM` / corners.

**Move:** `ReleaseCapture` then `QWindow.startSystemMove()` on icon and caption. Do **not** send `WM_NCLBUTTONDOWN`. Do **not** return `HTCAPTION`.

**Coordinates:** `ScreenToClient` on the HWND, then divide by `devicePixelRatioF()`. Hit-test in **window-local** logical pixels.

**Resize inset:** 4px, and skipped on interactive chrome widgets so close/max stay fully clickable.

**Color:** chrome `#F3F3F3` (Notepad tab strip); selected tab and editor `#FFFFFF`. No status bar.

## 4. Non-goals

- File / Edit / View / formatting toolbar
- Snap Layouts via `HTMAXBUTTON` (that path breaks the painted maximize button)
- Changing Markdown save/open or PPTX visual

## 5. Testing

- Min/max/close and caption → `HTCLIENT`; left empty edge → `HTLEFT`
- Two caption presses both call `startSystemMove`
- Clicking maximize button emits maximize (Qt click path)
- Chrome stylesheet `#f3f3f3`; editor `#ffffff` / `NoFrame`
- Existing window/IPC tests stay green; frozen smoke + desktop shortcut
