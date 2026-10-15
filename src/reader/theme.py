from __future__ import annotations

PAPER = "#f4efe6"
CHROME = "#ebe4d8"
INK = "#1c1915"
MUTED = "#8a8176"
COBALT = "#2563eb"
COBALT_HOVER = "#1d4ed8"
CARD = "#fffaf2"
LINE = "#e4d9c7"
HOVER = "#e4dccf"
PRESSED = "#d4cbb8"
CLOSE_HOVER = "#e81123"

# The UI font must contain every glyph it shows: a missing glyph makes Qt search
# all installed fonts on the GUI thread (seconds per search). YaHei UI covers
# Chinese and takes its Latin glyphs from Segoe UI. Name exactly one family in
# stylesheets: each extra family costs about 2 s to build a fallback chain.
UI_FONT_FAMILY = "Microsoft YaHei UI"
UI_FONT_STACK = f'"{UI_FONT_FAMILY}"'
# Caption/toolbar symbols (✕ ❐ ⟳ ...) that the UI font lacks.
SYMBOL_FONT_FAMILY = "Segoe UI Symbol"


def document_style() -> str:
    return (
        f"body{{margin:0;background:{PAPER};color:{INK};"
        'font-family:Candara,Calibri,"Segoe UI",sans-serif;'
        "padding:36px 48px 72px;line-height:1.72}"
        f"a{{color:{COBALT}}}"
        f"h1,h2,h3{{color:{INK};line-height:1.32}}"
        f"h1,h2{{border-bottom:1px solid {LINE};padding-bottom:.35rem}}"
        "table{border-collapse:collapse;width:100%}"
        f"td,th{{border:1px solid {LINE};padding:.55rem .7rem}}"
        f"th{{background:{CARD}}}"
        f"pre,code{{background:{CARD}}}"
        "nav a{margin-right:12px}"
        f".slide{{border:1px solid {LINE};margin:12px 0;padding:16px;"
        f"background:{CARD};border-radius:10px}}"
    )


def wrap_document_html(body: str, extra_css: str = "") -> str:
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<style>{document_style()}{extra_css}</style></head>"
        f"<body>{body}</body></html>"
    )
