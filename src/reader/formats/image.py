from pathlib import Path

from reader.preview.result import PreviewResult

IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"})


def to_preview(path: Path) -> PreviewResult:
    resolved = Path(path).resolve()
    return PreviewResult(
        html="",
        status_label="内置预览",
        kind="image",
        image_path=resolved,
    )
