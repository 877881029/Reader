from pathlib import Path


def test_to_preview_points_at_source_without_asset_dir(tmp_path: Path):
    from reader.formats.svg import to_preview

    path = tmp_path / "icon.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"/>',
        encoding="utf-8",
    )
    result = to_preview(path)
    assert result.kind == "svg"
    assert result.status_label == "内置预览"
    assert result.svg_path == path.resolve()
    assert result.asset_dir is None
    assert result.html == ""
