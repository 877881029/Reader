from pathlib import Path

from reader.preview.result import PreviewResult

BINARY_SUFFIXES = frozenset({".bin"})


def to_preview(path: Path) -> PreviewResult:
    """The hex view maps the file itself; never read it here."""
    return PreviewResult(
        html="",
        status_label="二进制预览",
        kind="binary",
        binary_path=Path(path).resolve(),
    )