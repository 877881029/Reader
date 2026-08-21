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


def test_pptx_uses_office_when_available(tmp_path: Path):
    p = tmp_path / "a.pptx"
    p.write_bytes(b"not-a-real-pptx")
    office = FakeOffice(available=True)
    result = preview(p, office=office)
    assert office.calls == [p]
    assert result.status_label == "Office 预览"
    assert "office" in result.html


def test_xlsx_uses_office_when_available(tmp_path: Path):
    p = tmp_path / "a.xlsx"
    p.write_bytes(b"not-a-real-xlsx")
    office = FakeOffice(available=True)
    result = preview(p, office=office)
    assert office.calls == [p]
    assert result.status_label == "Office 预览"
    assert "office" in result.html


def test_pptx_falls_back_when_office_missing(tmp_path: Path):
    from pptx import Presentation

    p = tmp_path / "a.pptx"
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "pptx-fallback"
    prs.save(p)
    office = FakeOffice(available=False)
    result = preview(p, office=office)
    assert office.calls == []
    assert result.status_label == "内置预览"
    assert "pptx-fallback" in result.html


def test_xlsx_falls_back_when_office_missing(tmp_path: Path):
    from openpyxl import Workbook

    p = tmp_path / "a.xlsx"
    wb = Workbook()
    wb.active.append(["xlsx-fallback-cell"])
    wb.save(p)
    office = FakeOffice(available=False)
    result = preview(p, office=office)
    assert office.calls == []
    assert result.status_label == "内置预览"
    assert "xlsx-fallback-cell" in result.html


def test_builtin_renderer_error_propagates(tmp_path: Path, monkeypatch):
    from reader.preview import pipeline

    def boom(_path: Path) -> PreviewResult:
        raise ValueError("builtin parse failed")

    monkeypatch.setitem(pipeline._BUILTIN, ".md", boom)
    p = tmp_path / "a.md"
    p.write_text("# x", encoding="utf-8")
    with pytest.raises(ValueError, match="builtin parse failed"):
        preview(p)


def test_unsupported_raises(tmp_path: Path):
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF")
    with pytest.raises(SniffError):
        preview(p)
