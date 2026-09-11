from pathlib import Path

from reader.formats.code import language_for, to_preview


def test_code_preview_keeps_text_and_kind(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text('{\n  "ok": true\n}\n', encoding="utf-8")
    result = to_preview(path)
    assert result.kind == "code"
    assert result.status_label == "代码预览"
    assert result.error is None
    assert '"ok": true' in result.html
    assert language_for(".json") == "json"
    assert language_for(".yaml") == "yaml"
    assert language_for(".yml") == "yaml"
    assert language_for(".xml") == "xml"
    assert language_for(".c") == "c"
    assert language_for(".h") == "c"


def test_code_preview_replaces_invalid_utf8(tmp_path: Path):
    path = tmp_path / "odd.xml"
    path.write_bytes(b"<root>\xff</root>")
    result = to_preview(path)
    assert result.kind == "code"
    assert "\ufffd" in result.html
