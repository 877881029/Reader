# Welcome Path Lookup (Ctrl+F)

Date: 2026-09-11  
Status: Implemented (hidden path box on the recent heading)  
Progress ledger: `docs/STATUS.md`

## 1. Goal

On the **welcome page right column only**, Ctrl+F reveals a path field on the same row as **最近打开**. Enter a directory and press Enter to list openable files in that folder (same cards as recents). Enter a file path and press Enter to open it. Left column and paper tokens do not change.

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.

## 2. Decisions

| Topic | Choice |
|---|---|
| Where | Right column heading row: `最近打开` + hidden `QLineEdit` |
| Reveal | Ctrl+F while welcome is showing. Window document FindBar stays hidden |
| Submit | Enter. Directory → list supported files in that folder (not recursive). File → `open_paths` |
| List UI | Reuse recent cards (`welcomeRecentList` / badge / name / path) |
| Empty | Same empty-label slot; copy `没有可打开的文件` while lookup listing is empty |
| Esc | Hide the field, restore recents |
| Strip | Quotes and surrounding whitespace; `expanduser` |
| Left | Brand, Open, New Markdown, `emptyWindowHint` unchanged |
| Theme | Paper / card / line / ink / muted / cobalt only |

Unsupported / missing paths do not open; directory listing shows only `SUPPORTED_EXTENSIONS` files, sorted by name.

## 3. Non-goals

- Recursive search, glob, or full-text search of file contents
- Changing the window FindBar used on document tabs
- Left-column controls or new heading text

## 4. Testing

- Ctrl+F on welcome: lookup visible, FindBar still hidden, left hint unchanged
- Enter on a folder lists matching files as recent-style rows
- Enter on a file emits open / opens a tab
- Esc restores recents and hides the field
- Caption hit tests stay green
