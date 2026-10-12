# New-Tab Menu and Markdown Mode Switch Design

Status: Approved
Progress ledger: `docs/STATUS.md`

## Background

The title-bar `+` button creates an untitled Markdown draft immediately. The
user wants a Copilot-style dropdown instead, with icons, and a visible switch
between Markdown edit and preview modes (today only `Ctrl+I` / `Ctrl+T`).

## Scope

1. `+` opens a rounded, icon-led menu (object name `tabNewMenu`):
   - **新建文件** — same as today: untitled Markdown draft (default action).
   - **打开文件** — the existing open dialog filtered to supported formats.
   - **Browser** — listed, disabled, tooltip `即将推出`.
   - **Terminal** — listed, disabled, tooltip `即将推出`.
   Icons are line icons painted at runtime in the `INK` colour (no new asset
   files, no network, frozen-build safe).
2. A segmented `编辑 | 预览` switch (`markdownModeSwitch`) in the title chrome,
   visible only when the current tab is Markdown. The checked segment mirrors
   the current mode; clicking the other segment triggers the existing
   `actionMarkdownEdit` / `actionMarkdownPreview`, so save-before-preview and
   cancel semantics stay identical to the shortcuts.

## Non-goals

- Browser and Terminal behaviour.
- New keyboard shortcuts; `Ctrl+N`, `Ctrl+O`, `Ctrl+I`, `Ctrl+T` unchanged.

## Constraints

- Do not modify `hit_test_local`, `begin_window_move`, or `nativeEvent`; the new
  switch is registered as interactive chrome so clicks never start a window move.
- `add_blank_tab` and `actionNewTab` keep creating a Markdown draft directly.

## Acceptance

- Clicking `+` shows the menu with the four items in order and icons on each;
  only the first two are enabled.
- 新建文件 adds `未命名.md`; 打开文件 opens the supported-format dialog.
- The mode switch is hidden for non-Markdown tabs, shows the right checked
  segment, and toggles modes through the existing actions.