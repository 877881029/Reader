# Paper Theme Across Open Documents

Date: 2026-09-10  
Status: Approved by user (extend welcome palette; implement without extra gates)  
Progress ledger: `docs/STATUS.md`

## 1. Goal

The empty-launch welcome page (warm paper `#f4efe6`, ink `#1c1915`, cobalt `#2563eb`) is the product surface. Opening `.md` / `.docx` / `.pptx` / `.xlsx` / `.pdf` must continue that surface instead of snapping to cold notepad gray/white or the PPTX viewer’s dark shell.

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`. Slide canvases and PDF page pixels stay as authored (white slide / PDF content).

## 2. Tokens (`reader.theme`)

| Token | Hex | Use |
|---|---|---|
| `PAPER` | `#f4efe6` | Page fill, selected tab, document body, markdown paper |
| `CHROME` | `#ebe4d8` | Title strip, unselected chrome, PPTX rail/toolbar |
| `INK` | `#1c1915` | Body and tab text |
| `MUTED` | `#8a8176` | Secondary text |
| `COBALT` | `#2563eb` | Links, active thumb, welcome actions |
| `CARD` | `#fffaf2` | Recent slips, tables/code, PPTX text-slide cards |
| `LINE` | `#e4d9c7` | Hairlines |

Close-button hover stays Windows red `#e81123`.

## 3. Surfaces

- Window root, content stack, tab pane, markdown editor: `PAPER`. Title chrome: `CHROME`; selected tab: `PAPER`.
- Markdown visual bundle and HTML fallbacks (md/docx/xlsx/pptx-text): paper body, cobalt links.
- PPTX visual chrome (rail/toolbar/stage): paper/cobalt. Host that draws the slide stays white.
- PDF: WebEngine page background paper; Chromium’s built-in viewer chrome is not restyled.
- Welcome page reads the same tokens.

## 4. Testing

- Token file and wrap helper emit `PAPER` / `COBALT`.
- Chrome / root / editor stylesheets use the new hex values.
- Format HTML includes paper background.
- Source CSS for md-viewer and pptx-viewer uses paper tokens (pptx no longer `#0f172a`).
- Caption-move and min/max hit tests stay green.
