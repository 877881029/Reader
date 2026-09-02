# Notepad Title Surface Polish Design

Date: 2026-09-02  
Status: Approved by user (continuous execute; drag/buttons must stay working)  
Depends on: `docs/superpowers/specs/2026-09-02-notepad-chrome-hittest-design.md`  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Match Windows 11 Notepad’s top surface:

1. The **whole title strip** (icon, unused chrome, `+`, min/max/close) is light gray.
2. The **selected tab** is the same white as the editor, sitting flush so there is no gray “shelf” between tab and page.
3. Window buttons stay on that gray and show a light hover (close hover red).
4. **Do not change** hit-testing, `startSystemMove`, button click wiring, or resize borders.

## 2. Problem

`centralWidget` uses `setStyleSheet("background: #ffffff")`, which Qt applies to descendants. Caption, tab bar, and window buttons paint white, so the strip looks like a white bar instead of Notepad gray even though `#titleChrome` is `#F3F3F3`.

## 3. Architecture

- Scope root fill to `#readerRoot { background: #ffffff; }` so it cannot leak into chrome.
- Chrome and idle window buttons: `#F3F3F3`.
- Selected tab: `#FFFFFF`, no bottom margin, top radii only — attaches to the white pane.
- Unselected tabs: transparent on gray; hover `#E8E8E8`.
- Min/max hover `#E5E5E5`; close hover `#E81123` / white glyph.
- Leave `hit_test_local`, `begin_window_move`, `nativeEvent`, and button `clicked` connections untouched.

## 4. Testing

- Existing caption-move and min/max click tests still pass.
- Stylesheet asserts: chrome `#f3f3f3`, selected tab `#ffffff`, min/max hover, close hover red.
- Root stylesheet is `#readerRoot`, not a bare `background` on all children.
