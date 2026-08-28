from pathlib import Path

import pytest

from reader.preview.pipeline import preview

DOWNLOADS = Path.home() / "Downloads"
MD = DOWNLOADS / "component-release-cross-component-scaling.md"


@pytest.mark.skipif(not MD.exists(), reason="downloads markdown missing")
def test_real_markdown_from_downloads():
    result = preview(MD)
    assert result.kind == "markdown"
    assert result.html == ""
    assert result.fallback_html
    assert result.status_label == "内置预览（视觉模式）"
