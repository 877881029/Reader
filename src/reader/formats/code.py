from __future__ import annotations

from pathlib import Path

from reader.preview.result import PreviewResult

C_FAMILY_SUFFIXES = frozenset(
    {".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".hh", ".hxx", ".inl", ".ipp"}
)
CODE_SUFFIXES = frozenset(
    {".json", ".yaml", ".yml", ".xml", ".txt"} | C_FAMILY_SUFFIXES
)


def language_for(suffix: str) -> str:
    value = suffix.lower()
    if value in {".yaml", ".yml"}:
        return "yaml"
    if value == ".xml":
        return "xml"
    if value in C_FAMILY_SUFFIXES:
        return "c"
    if value == ".txt":
        return "text"
    return "json"


def to_preview(path: Path) -> PreviewResult:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    label = "文本预览" if Path(path).suffix.lower() == ".txt" else "代码预览"
    return PreviewResult(html=text, status_label=label, kind="code")
