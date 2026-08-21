from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import shutil
import tempfile
from typing import Any

from reader.preview.result import PreviewResult

try:
    import pythoncom
except Exception:  # pragma: no cover - depends on host environment
    pythoncom = None  # type: ignore[assignment]

try:
    from win32com.client import Dispatch
except Exception:  # pragma: no cover - depends on host environment
    Dispatch = None  # type: ignore[assignment]


_PROGIDS: dict[str, str] = {
    ".docx": "Word.Application",
    ".pptx": "PowerPoint.Application",
    ".xlsx": "Excel.Application",
}


@contextmanager
def _com_scope():
    if pythoncom is None:
        yield
        return
    pythoncom.CoInitialize()
    try:
        yield
    finally:
        pythoncom.CoUninitialize()


def _quit_app(app: Any) -> None:
    if app is None:
        return
    try:
        app.Quit()
    except Exception:
        pass


def _can_dispatch(progid: str) -> bool:
    if Dispatch is None:
        return False
    with _com_scope():
        app = None
        try:
            app = Dispatch(progid)
            return True
        except Exception:
            return False
        finally:
            _quit_app(app)


def office_available(suffix: str) -> bool:
    progid = _PROGIDS.get(suffix.lower())
    if progid is None:
        return False
    return _can_dispatch(progid)


def _open_document(app: Any, suffix: str, path: Path) -> Any:
    if suffix == ".docx":
        return app.Documents.Open(str(path))
    if suffix == ".pptx":
        return app.Presentations.Open(str(path), WithWindow=False)
    if suffix == ".xlsx":
        return app.Workbooks.Open(str(path))
    raise ValueError(f"Unsupported Office suffix: {suffix}")


def _export_pdf(document: Any, suffix: str, pdf_path: Path) -> None:
    if suffix == ".docx":
        document.ExportAsFixedFormat(OutputFileName=str(pdf_path), ExportFormat=17)
        return
    if suffix == ".pptx":
        document.ExportAsFixedFormat(PathName=str(pdf_path), FixedFormatType=2)
        return
    if suffix == ".xlsx":
        document.ExportAsFixedFormat(Type=0, Filename=str(pdf_path))
        return
    raise ValueError(f"Unsupported Office suffix: {suffix}")


def _save_html(document: Any, suffix: str, html_path: Path) -> None:
    if suffix == ".docx":
        document.SaveAs(FileName=str(html_path), FileFormat=10)
        return
    if suffix == ".pptx":
        document.SaveAs(FileName=str(html_path), FileFormat=12)
        return
    if suffix == ".xlsx":
        document.SaveAs(FileName=str(html_path), FileFormat=44)
        return
    raise ValueError(f"Unsupported Office suffix: {suffix}")


def _close_document(document: Any, suffix: str) -> None:
    try:
        if suffix == ".pptx":
            document.Close()
        else:
            document.Close(SaveChanges=False)
    except Exception:
        pass


class Win32OfficeBackend:
    def available_for(self, suffix: str) -> bool:
        return office_available(suffix)

    def export(self, path: Path) -> PreviewResult:
        src = Path(path).resolve()
        suffix = src.suffix.lower()
        progid = _PROGIDS.get(suffix)
        if progid is None:
            raise ValueError(f"Unsupported Office suffix: {suffix}")
        if Dispatch is None:
            raise RuntimeError("pywin32 is unavailable")

        with _com_scope():
            app = None
            document = None
            export_dir = Path(tempfile.mkdtemp(prefix="reader-office-"))
            keep_export_dir = False
            try:
                app = Dispatch(progid)
                document = _open_document(app, suffix, src)
                pdf_path = export_dir / f"{src.stem}.reader.pdf"
                try:
                    _export_pdf(document, suffix, pdf_path)
                    keep_export_dir = True
                    return PreviewResult(
                        html="",
                        status_label="Office 预览",
                        kind="pdf",
                        asset_dir=export_dir,
                        pdf_path=pdf_path,
                    )
                except Exception:
                    html_path = export_dir / f"{src.stem}.reader.html"
                    _save_html(document, suffix, html_path)
                    return PreviewResult(
                        html=html_path.read_text(encoding="utf-8", errors="ignore"),
                        status_label="Office 预览",
                        kind="html",
                    )
            finally:
                _close_document(document, suffix)
                _quit_app(app)
                if not keep_export_dir:
                    shutil.rmtree(export_dir, ignore_errors=True)
