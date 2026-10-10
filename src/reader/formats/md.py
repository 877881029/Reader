from pathlib import Path

from markdown_it import MarkdownIt

from reader.preview.result import PreviewResult
from reader.text_io import read_text_file
from reader.theme import wrap_document_html

_MD = MarkdownIt("commonmark", {"html": False}).enable("table")


def _read(path: Path) -> str:
    return read_text_file(Path(path)).text


def to_html(path: Path) -> PreviewResult:
    text = _read(path)
    body = _MD.render(text)
    html = wrap_document_html(body)
    return PreviewResult(html=html, status_label="内置预览", kind="html")


def to_visual(path: Path) -> PreviewResult:
    fallback = to_html(path)
    return PreviewResult(
        html="",
        fallback_html=fallback.html,
        status_label="内置预览（视觉模式）",
        kind="markdown",
    )
