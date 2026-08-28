from pathlib import Path

from markdown_it import MarkdownIt

from reader.preview.result import PreviewResult

_MD = MarkdownIt("commonmark", {"html": False}).enable("table")


def _read(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def to_html(path: Path) -> PreviewResult:
    text = _read(path)
    body = _MD.render(text)
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<style>body{font-family:Segoe UI,sans-serif;padding:16px}"
        "table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px}"
        "pre{background:#f5f5f5;padding:8px;overflow:auto}</style>"
        f"</head><body>{body}</body></html>"
    )
    return PreviewResult(html=html, status_label="内置预览", kind="html")


def to_visual(path: Path) -> PreviewResult:
    fallback = to_html(path)
    return PreviewResult(
        html="",
        fallback_html=fallback.html,
        status_label="内置预览（视觉模式）",
        kind="markdown",
    )
