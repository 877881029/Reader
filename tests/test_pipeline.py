from pathlib import Path

import pytest

from reader.preview.pipeline import preview
from reader.preview.result import PreviewResult
from reader.sniff import SniffError


class FakeOffice:
    def __init__(self, available=True, boom=False):
        self.available = available
        self.boom = boom
        self.calls = []

    def available_for(self, suffix: str) -> bool:
        return self.available and suffix in {".docx", ".pptx", ".xlsx"}

    def export(self, path: Path) -> PreviewResult:
        self.calls.append(path)
        if self.boom:
            raise RuntimeError("COM busy")
        return PreviewResult(html="<p>office</p>", status_label="Office 预览", kind="html")


def test_md_never_uses_office(tmp_path: Path):
    p = tmp_path / "a.md"
    p.write_text("# Z", encoding="utf-8")
    office = FakeOffice(available=True)
    result = preview(p, office=office)
    assert office.calls == []
    assert result.status_label == "内置预览"
    assert "Z" in result.html


def test_docx_uses_office_when_available(tmp_path: Path):
    p = tmp_path / "a.docx"
    p.write_bytes(b"not-a-real-docx")
    office = FakeOffice(available=True)
    result = preview(p, office=office)
    assert office.calls == [p]
    assert result.status_label == "Office 预览"
    assert "office" in result.html


def test_docx_falls_back_when_office_missing(tmp_path: Path):
    from docx import Document

    p = tmp_path / "a.docx"
    d = Document()
    d.add_paragraph("fallback-body")
    d.save(p)
    office = FakeOffice(available=False)
    result = preview(p, office=office)
    assert office.calls == []
    assert result.status_label == "内置预览"
    assert "fallback-body" in result.html


def test_docx_falls_back_when_export_raises(tmp_path: Path):
    from docx import Document

    p = tmp_path / "a.docx"
    d = Document()
    d.add_paragraph("after-com-fail")
    d.save(p)
    office = FakeOffice(available=True, boom=True)
    result = preview(p, office=office)
    assert result.status_label == "内置预览"
    assert "after-com-fail" in result.html


def test_unsupported_raises(tmp_path: Path):
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF")
    with pytest.raises(SniffError):
        preview(p)
