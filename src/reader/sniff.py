from pathlib import Path

SUPPORTED_EXTENSIONS = frozenset({".docx", ".pptx", ".xlsx", ".md"})


class SniffError(Exception):
    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"{reason}: {path}")


def sniff(path: Path) -> str:
    path = Path(path)
    if not path.exists():
        raise SniffError(path, "not_found")
    if not path.is_file():
        raise SniffError(path, "not_a_file")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise SniffError(path, "unsupported_extension")
    return suffix
