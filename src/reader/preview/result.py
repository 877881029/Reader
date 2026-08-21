from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PreviewResult:
    html: str
    status_label: str
    kind: str = "html"
    asset_dir: Path | None = None
    pdf_path: Path | None = None
    error: str | None = None
