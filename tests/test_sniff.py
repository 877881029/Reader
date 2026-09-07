from pathlib import Path
import pytest
from reader.sniff import sniff, SniffError, SUPPORTED_EXTENSIONS

def test_supported_extensions():
    assert SUPPORTED_EXTENSIONS == frozenset({".docx", ".pptx", ".xlsx", ".md", ".pdf"})

@pytest.mark.parametrize("name,suffix", [
    ("a.DOCX", ".docx"),
    ("b.pptx", ".pptx"),
    ("c.Xlsx", ".xlsx"),
    ("d.MD", ".md"),
    ("e.PDF", ".pdf"),
])
def test_sniff_accepts_supported(tmp_file, name, suffix):
    path = tmp_file(name)
    assert sniff(path) == suffix

def test_sniff_accepts_pdf(tmp_file):
    path = tmp_file("x.pdf")
    assert sniff(path) == ".pdf"

def test_sniff_rejects_legacy_doc(tmp_file):
    with pytest.raises(SniffError) as ei:
        sniff(tmp_file("old.doc"))
    assert ei.value.reason == "unsupported_extension"

def test_sniff_rejects_missing(tmp_path: Path):
    missing = tmp_path / "nope.md"
    with pytest.raises(SniffError) as ei:
        sniff(missing)
    assert ei.value.reason == "not_found"

def test_sniff_rejects_directory(tmp_path: Path):
    with pytest.raises(SniffError) as ei:
        sniff(tmp_path)
    assert ei.value.reason == "not_a_file"
