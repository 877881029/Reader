from dataclasses import dataclass
from pathlib import Path
from typing import Literal

PreviewKind = Literal["html", "pdf", "pptx", "markdown", "error"]


@dataclass(frozen=True)
class PreviewResult:
    html: str
    status_label: str
    kind: PreviewKind = "html"
    asset_dir: Path | None = None
    pdf_path: Path | None = None
    fallback_html: str | None = None
    error: str | None = None
