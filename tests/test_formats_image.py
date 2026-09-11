from pathlib import Path


def test_to_preview_points_at_source_without_asset_dir(tmp_path: Path):
    from reader.formats.image import to_preview

    path = tmp_path / "shot.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    result = to_preview(path)
    assert result.kind == "image"
    assert result.status_label == "内置预览"
    assert result.image_path == path.resolve()
    assert result.asset_dir is None
    assert result.html == ""
