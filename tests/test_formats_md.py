from pathlib import Path

from reader.formats.md import to_html


def test_markdown_renders_heading_and_table(tmp_path: Path):
    src = tmp_path / "note.md"
    src.write_text(
        "# Hello\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\n```python\nprint(1)\n```\n",
        encoding="utf-8",
    )
    result = to_html(src)
    assert result.kind == "html"
    assert result.status_label == "内置预览"
    assert result.error is None
    assert "Hello" in result.html
    assert "<table" in result.html.lower()
    assert "<pre" in result.html.lower() or "print(1)" in result.html
