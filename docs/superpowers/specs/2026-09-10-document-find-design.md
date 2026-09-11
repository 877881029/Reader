# Document Find (Ctrl+F)

Date: 2026-09-10  
Status: Implemented (window find bar; Ctrl+F / F3 / Esc; wrap; match case)  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Any open document tab can search in-page with **Ctrl+F**, like Notepad: type a string, jump to the next match, optional match-case, wrap around, Esc to close.

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.

## 2. Decisions

| Topic | Choice |
|---|---|
| Scope | All open document tabs: `.md` / `.docx` / `.pptx` / `.xlsx` / `.pdf` / `.json` / `.yaml` / `.yml` / `.xml` / `.svg` / raster images |
| UI | Window-level find bar under the title chrome (not a modal dialog; not inside tab page layout) |
| Shortcut | `Ctrl+F` (`QKeySequence.StandardKey.Find`); `F3` / `Shift+F3` next/previous |
| Enter | In the search box: Enter = next, Shift+Enter = previous |
| Esc | Hide the bar and clear WebEngine highlights |
| Match case | Off by default; toggle in the bar |
| Wrap | Yes. If no later match, wrap; if none at all, show `未找到` |
| Replace | Out of scope |
| Welcome | Ctrl+F does nothing while the welcome page is showing |

Plain-text views (`MarkdownTextView`, `CodeTextView`) use `QPlainTextEdit.find`. HTML / Markdown visual / PPTX visual / PDF use `QWebEnginePage.findText`. Test label viewers match substring only.

## 3. Surfaces

- `FindBar` widget: paper/chrome tokens, query field, match-case, previous/next, close, `未找到`
- `MainWindow` ApplicationShortcut; bar sits between `TitleChrome` and `contentStack`
- Tab page layouts stay a single content widget so existing `layout.count() == 1` tests remain valid

## 4. Testing

- Helper: wrap + match-case on `QPlainTextEdit`; substring on `QLabel`
- Window: Ctrl+F shows bar on a document, ignored on welcome, Esc hides, next match selects text
- Caption hit tests stay green
