from pathlib import Path

import pytest

from reader.preview.office import Win32OfficeBackend, office_available


class FakeWordDocument:
    def __init__(self, export_ok: bool = True):
        self.export_ok = export_ok
        self.closed = 0
        self.pdf_calls: list[tuple[str, int]] = []
        self.html_calls: list[tuple[str, int]] = []

    def ExportAsFixedFormat(self, OutputFileName: str, ExportFormat: int):
        self.pdf_calls.append((OutputFileName, ExportFormat))
        if not self.export_ok:
            raise RuntimeError("pdf export failed")
        Path(OutputFileName).write_bytes(b"%PDF-word")

    def SaveAs(self, FileName: str, FileFormat: int):
        self.html_calls.append((FileName, FileFormat))
        Path(FileName).write_text("<html>office-html</html>", encoding="utf-8")

    def Close(self, SaveChanges=False):
        self.closed += 1


class FakeWordDocumentHtmlFail(FakeWordDocument):
    def SaveAs(self, FileName: str, FileFormat: int):
        self.html_calls.append((FileName, FileFormat))
        raise RuntimeError("html export failed")


class FakePptPresentation:
    def __init__(self):
        self.closed = 0
        self.pdf_calls: list[tuple[str, int]] = []

    def ExportAsFixedFormat(self, PathName: str, FixedFormatType: int):
        self.pdf_calls.append((PathName, FixedFormatType))
        Path(PathName).write_bytes(b"%PDF-ppt")

    def SaveAs(self, FileName: str, FileFormat: int):
        Path(FileName).write_text("<html>ppt-html</html>", encoding="utf-8")

    def Close(self):
        self.closed += 1


class FakeExcelWorkbook:
    def __init__(self):
        self.closed = 0
        self.pdf_calls: list[tuple[int, str]] = []

    def ExportAsFixedFormat(self, Type: int, Filename: str):
        self.pdf_calls.append((Type, Filename))
        Path(Filename).write_bytes(b"%PDF-xlsx")

    def SaveAs(self, FileName: str, FileFormat: int):
        Path(FileName).write_text("<html>xlsx-html</html>", encoding="utf-8")

    def Close(self, SaveChanges=False):
        self.closed += 1


class _Collection:
    def __init__(self, doc: object):
        self.doc = doc
        self.opened_paths: list[str] = []
        self.opened_kwargs: list[dict[str, object]] = []

    def Open(self, path: str, **_kwargs):
        self.opened_paths.append(path)
        self.opened_kwargs.append(dict(_kwargs))
        return self.doc


class FakeWordApp:
    def __init__(self, doc: FakeWordDocument):
        self.Documents = _Collection(doc)
        self.quit_calls = 0

    def Quit(self):
        self.quit_calls += 1


class FakePptApp:
    def __init__(self, doc: FakePptPresentation):
        self.Presentations = _Collection(doc)
        self.quit_calls = 0

    def Quit(self):
        self.quit_calls += 1


class FakeExcelApp:
    def __init__(self, doc: FakeExcelWorkbook):
        self.Workbooks = _Collection(doc)
        self.quit_calls = 0

    def Quit(self):
        self.quit_calls += 1


def test_available_false_for_unsupported_suffix():
    assert office_available(".md") is False


def test_available_false_when_dispatch_missing(monkeypatch):
    monkeypatch.setattr("reader.preview.office.Dispatch", None)
    assert office_available(".docx") is False


def test_export_docx_pdf_success_and_cleanup(tmp_path, monkeypatch):
    src = tmp_path / "a.docx"
    src.write_bytes(b"x")
    doc = FakeWordDocument(export_ok=True)
    app = FakeWordApp(doc)
    coinit_calls = []

    def fake_dispatch(name: str):
        assert name == "Word.Application"
        return app

    monkeypatch.setattr("reader.preview.office.Dispatch", fake_dispatch)
    monkeypatch.setattr(
        "reader.preview.office.pythoncom",
        type(
            "PC",
            (),
            {
                "CoInitialize": staticmethod(lambda: coinit_calls.append("init")),
                "CoUninitialize": staticmethod(lambda: coinit_calls.append("uninit")),
            },
        ),
    )

    result = Win32OfficeBackend().export(src)
    assert result.kind == "pdf"
    assert result.status_label == "Office 预览"
    assert result.pdf_path is not None
    assert result.pdf_path.read_bytes().startswith(b"%PDF")
    assert doc.pdf_calls and doc.pdf_calls[0][1] == 17
    assert doc.closed == 1
    assert app.quit_calls == 1
    assert coinit_calls == ["init", "uninit"]


def test_export_docx_html_fallback_when_pdf_fails(tmp_path, monkeypatch):
    src = tmp_path / "a.docx"
    src.write_bytes(b"x")
    doc = FakeWordDocument(export_ok=False)
    app = FakeWordApp(doc)

    def fake_dispatch(name: str):
        assert name == "Word.Application"
        return app

    monkeypatch.setattr("reader.preview.office.Dispatch", fake_dispatch)
    monkeypatch.setattr("reader.preview.office.pythoncom", None)

    result = Win32OfficeBackend().export(src)
    assert result.kind == "html"
    assert "office-html" in result.html
    assert doc.html_calls and doc.html_calls[0][1] == 10
    assert doc.closed == 1
    assert app.quit_calls == 1


def test_export_docx_pdf_keeps_source_dir_clean(tmp_path, monkeypatch):
    src = tmp_path / "a.docx"
    src.write_bytes(b"x")
    doc = FakeWordDocument(export_ok=True)
    app = FakeWordApp(doc)
    monkeypatch.setattr("reader.preview.office.Dispatch", lambda name: app)
    monkeypatch.setattr("reader.preview.office.pythoncom", None)

    result = Win32OfficeBackend().export(src)
    assert result.kind == "pdf"
    assert result.pdf_path is not None
    assert result.pdf_path.parent != src.parent
    assert sorted(p.name for p in src.parent.iterdir()) == ["a.docx"]


def test_export_docx_html_fallback_keeps_source_dir_clean(tmp_path, monkeypatch):
    src = tmp_path / "a.docx"
    src.write_bytes(b"x")
    doc = FakeWordDocument(export_ok=False)
    app = FakeWordApp(doc)
    monkeypatch.setattr("reader.preview.office.Dispatch", lambda name: app)
    monkeypatch.setattr("reader.preview.office.pythoncom", None)

    result = Win32OfficeBackend().export(src)
    assert result.kind == "html"
    assert sorted(p.name for p in src.parent.iterdir()) == ["a.docx"]
    assert doc.html_calls
    html_out = Path(doc.html_calls[0][0])
    assert html_out.parent != src.parent
    assert not html_out.exists()


def test_export_docx_failure_still_cleans_up_and_uninitializes(tmp_path, monkeypatch):
    src = tmp_path / "a.docx"
    src.write_bytes(b"x")
    doc = FakeWordDocumentHtmlFail(export_ok=False)
    app = FakeWordApp(doc)
    coinit_calls = []

    monkeypatch.setattr("reader.preview.office.Dispatch", lambda _name: app)
    monkeypatch.setattr(
        "reader.preview.office.pythoncom",
        type(
            "PC",
            (),
            {
                "CoInitialize": staticmethod(lambda: coinit_calls.append("init")),
                "CoUninitialize": staticmethod(lambda: coinit_calls.append("uninit")),
            },
        ),
    )

    with pytest.raises(RuntimeError, match="html export failed"):
        Win32OfficeBackend().export(src)

    assert sorted(p.name for p in src.parent.iterdir()) == ["a.docx"]
    assert doc.closed == 1
    assert app.quit_calls == 1
    assert coinit_calls == ["init", "uninit"]


def test_export_pptx_uses_presentation_api(tmp_path, monkeypatch):
    src = tmp_path / "a.pptx"
    src.write_bytes(b"x")
    doc = FakePptPresentation()
    app = FakePptApp(doc)

    def fake_dispatch(name: str):
        assert name == "PowerPoint.Application"
        return app

    monkeypatch.setattr("reader.preview.office.Dispatch", fake_dispatch)
    monkeypatch.setattr("reader.preview.office.pythoncom", None)

    result = Win32OfficeBackend().export(src)
    assert result.kind == "pdf"
    assert doc.pdf_calls and doc.pdf_calls[0][1] == 2
    assert app.Presentations.opened_kwargs == [{"WithWindow": False}]
    assert doc.closed == 1
    assert app.quit_calls == 1


def test_export_xlsx_uses_workbook_api(tmp_path, monkeypatch):
    src = tmp_path / "a.xlsx"
    src.write_bytes(b"x")
    doc = FakeExcelWorkbook()
    app = FakeExcelApp(doc)

    def fake_dispatch(name: str):
        assert name == "Excel.Application"
        return app

    monkeypatch.setattr("reader.preview.office.Dispatch", fake_dispatch)
    monkeypatch.setattr("reader.preview.office.pythoncom", None)

    result = Win32OfficeBackend().export(src)
    assert result.kind == "pdf"
    assert doc.pdf_calls and doc.pdf_calls[0][0] == 0
    assert doc.closed == 1
    assert app.quit_calls == 1


def test_export_raises_for_unsupported_suffix(tmp_path):
    src = tmp_path / "a.md"
    src.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported Office suffix"):
        Win32OfficeBackend().export(src)
