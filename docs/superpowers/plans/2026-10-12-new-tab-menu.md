# New-Tab Menu and Markdown Mode Switch Implementation Plan

Status: Implemented

> Execute tasks in order. For each task: observe RED, implement GREEN, run the
> focused suite, update `docs/STATUS.md`, commit, and push `origin/main`.

**Spec:** `docs/superpowers/specs/2026-10-12-new-tab-menu-design.md`

## Task 1: `+` dropdown menu with icons

**RED** window tests: clicking `+` pops `tabNewMenu`; items 新建文件 / 打开文件 /
Browser / Terminal in order, all with non-null icons, last two disabled;
新建文件 adds an untitled Markdown tab; 打开文件 invokes the open dialog.
**GREEN** `src/reader/shell/icons.py` painted line icons; `TitleChrome`
pops a menu below `+`; window builds the menu.

## Task 2: Markdown edit/preview switch

**RED** window tests: switch hidden on welcome/non-md tabs; on md visual tab
`预览` checked; clicking `编辑` enters text mode; clicking `预览` returns to
visual; switch is interactive chrome (no window move).
**GREEN** segmented control in `TitleChrome`, refreshed from
`_refresh_preview_actions`.

## Task 3: Docs and release gate

Update README and 功能全解, run `verify.ps1 -Release`, mark spec/plan
Implemented, record evidence.