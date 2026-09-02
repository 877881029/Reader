# Notepad Spacing and Surface Polish Design

Date: 2026-09-02  
Status: Approved by user (continuous execute)  
Depends on: `docs/superpowers/specs/2026-09-02-notepad-title-surface-design.md`  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Four visual gaps versus Windows 11 Notepad, without touching drag or window-button hit-testing:

1. The **+** sits immediately after the last tab (no extra gap).
2. The **editor** is Notepad’s soft page color `#F9F9F9`, not pure `#FFFFFF`.
3. The **window** uses Win11 rounded corners (`DWMWCP_ROUND`). Tabs keep small top radii.
4. **Text starts just under the title strip** — the empty band is the reparented `QTabWidget` still reserving tab-bar height.

## 2. Architecture

- Cluster `titleTabHost` + `tabNewButton` with layout spacing `0`; tab `margin-right: 0`.
- Page fill `#F9F9F9` on editor, selected tab, tab pane, content stack, `#readerRoot`.
- `ChromeTabWidget.resizeEvent` stretches the internal stack to the full widget rect so no ghost tab-bar gap.
- `DwmSetWindowAttribute(..., DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_ROUND)` on every show, even if frame styles were already applied.
- Editor `documentMargin` 8px (Notepad-like inset, not a second header).

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.

## 3. Testing

- Plus left edge within 2px of tab-host right edge.
- Untitled editor top within 12px of chrome bottom.
- Editor / selected tab / root use `#f9f9f9`.
- Existing caption-move and min/max click tests stay green.
