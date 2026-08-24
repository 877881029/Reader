from pathlib import Path
from typing import Literal, Protocol

from reader.formats import docx as fmt_docx
from reader.formats import md as fmt_md
from reader.formats import pptx as fmt_pptx
from reader.formats import xlsx as fmt_xlsx
from reader.preview.result import PreviewResult
from reader.sniff import sniff

_BUILTIN = {
    ".md": fmt_md.to_html,
    ".docx": fmt_docx.to_html,
    ".pptx": fmt_pptx.to_html,
    ".xlsx": fmt_xlsx.to_html,
}


class OfficeBackend(Protocol):
    def available_for(self, suffix: str) -> bool: ...

    def export(self, path: Path) -> PreviewResult: ...


PreviewMode = Literal["builtin", "office"]


def preview(
    path: Path,
    office: OfficeBackend | None = None,
    *,
    mode: PreviewMode = "builtin",
) -> PreviewResult:
    path = Path(path)
    suffix = sniff(path)
    if (
        mode == "office"
        and suffix != ".md"
        and office is not None
        and office.available_for(suffix)
    ):
        return office.export(path)
    return _BUILTIN[suffix](path)
