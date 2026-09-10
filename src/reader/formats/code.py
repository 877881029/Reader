from __future__ import annotations

from pathlib import Path

from reader.preview.result import PreviewResult

CODE_SUFFIXES = frozenset({".json", ".yaml", ".yml", ".xml"})


def language_for(suffix: str) -> str:
    value = suffix.lower()
    if value in {".yaml", ".yml"}:
        return "yaml"
    if value == ".xml":
        return "xml"
    return "json"


def to_preview(path: Path) -> PreviewResult:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return PreviewResult(html=text, status_label="代码预览", kind="code")
