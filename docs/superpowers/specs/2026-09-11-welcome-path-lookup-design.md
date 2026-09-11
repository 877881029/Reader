# Welcome Path Lookup (Ctrl+F)

Date: 2026-09-11  
Status: Implemented (hidden path box; folder cards walk one level)  
Progress ledger: `docs/STATUS.md`

## 1. Goal

On the **welcome page right column only**, Ctrl+F reveals a path field on the same row as **最近打开**. Enter a directory and press Enter to list **subfolders + openable files** in that folder (same cards as recents). Click a folder to put its path in the box and list that level. Enter a file path and press Enter to open it. Left column and paper tokens do not change.

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.

## 2. Decisions

| Topic | Choice |
|---|---|
| Where | Right column heading row: `最近打开` + hidden `QLineEdit` |
| Reveal | Ctrl+F while welcome is showing. Window document FindBar stays hidden |
| Submit | Enter. Directory → list **subfolders + supported files** in that folder (one level). File → `open_paths` |
| Folders | Shown as the same cards with badge `DIR`. Clicking a folder puts its path in the lookup box and lists that folder |
| Click file | Opens the file (unchanged) |
| List UI | Reuse recent cards (`welcomeRecentList` / badge / name / path) |
| Empty | Same empty-label slot; copy `没有可打开的文件` while lookup listing is empty |
| Esc | Hide the field, restore recents |
| Strip | Quotes and surrounding whitespace; `expanduser` |
| Left | Brand, Open, New Markdown, `emptyWindowHint` unchanged |
| Theme | Paper / card / line / ink / muted / cobalt only |

Unsupported / missing paths do not open; directory listing shows subfolders (not `.` hidden names) then `SUPPORTED_EXTENSIONS` files, each sorted by name. Clicking a folder navigates one level; it does not dump the whole tree.

## 3. Non-goals

- Recursive search of the whole tree in one Enter, glob, or full-text search of file contents
- Changing the window FindBar used on document tabs
- Left-column controls or new heading text

## 4. Testing

- Ctrl+F on welcome: lookup visible, FindBar still hidden, left hint unchanged
- Enter on a folder lists subfolders and matching files as recent-style rows
- Clicking a folder updates the path box and lists that folder
- Enter on a file emits open / opens a tab
- Esc restores recents and hides the field
- Caption hit tests stay green
