from pathlib import Path

from reader.preview.result import PreviewResult


def to_preview(path: Path) -> PreviewResult:
    resolved = Path(path).resolve()
    return PreviewResult(
        html="",
        status_label="内置预览",
        kind="svg",
        svg_path=resolved,
    )
