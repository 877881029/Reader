from pathlib import Path

from markdown_it import MarkdownIt

from reader.preview.result import PreviewResult

_MD = MarkdownIt("commonmark").enable("table")


def to_html(path: Path) -> PreviewResult:
    text = Path(path).read_text(encoding="utf-8")
    body = _MD.render(text)
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<style>body{font-family:Segoe UI,sans-serif;padding:16px}"
        "table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px}"
        "pre{background:#f5f5f5;padding:8px;overflow:auto}</style>"
        f"</head><body>{body}</body></html>"
    )
    return PreviewResult(html=html, status_label="内置预览", kind="html")
