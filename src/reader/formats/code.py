from __future__ import annotations

from pathlib import Path

from reader.preview.result import PreviewResult

CODE_SUFFIXES = frozenset({".json", ".yaml", ".yml", ".xml", ".c", ".h", ".txt"})


def language_for(suffix: str) -> str:
    value = suffix.lower()
    if value in {".yaml", ".yml"}:
        return "yaml"
    if value == ".xml":
        return "xml"
    if value in {".c", ".h"}:
        return "c"
    if value == ".txt":
        return "text"
    return "json"


def to_preview(path: Path) -> PreviewResult:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    label = "文本预览" if Path(path).suffix.lower() == ".txt" else "代码预览"
    return PreviewResult(html=text, status_label=label, kind="code")
