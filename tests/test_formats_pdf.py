from pathlib import Path

from reader.formats.pdf import to_preview


def test_to_preview_points_at_source_without_asset_dir(tmp_path: Path):
    path = tmp_path / "doc.pdf"
    path.write_bytes(b"%PDF-1.4\n")
    result = to_preview(path)
    assert result.kind == "pdf"
    assert result.status_label == "内置预览"
    assert result.pdf_path == path.resolve()
    assert result.asset_dir is None
    assert result.html == ""
