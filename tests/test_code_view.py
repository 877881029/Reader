from pathlib import Path

from PySide6.QtWidgets import QPlainTextEdit

from reader.preview.code_view import CodeTextView
from reader.preview.syntax import (
    CHighlighter,
    JsonHighlighter,
    XmlHighlighter,
    YamlHighlighter,
    highlighter_for,
)
from reader.theme import COBALT, MUTED, PAPER


def _layout_foregrounds(document) -> set[tuple[int, int, str]]:
    layout = document.firstBlock().layout()
    assert layout is not None
    return {
        (item.start, item.length, item.format.foreground().color().name().lower())
        for item in layout.formats()
    }


def test_highlighter_colors_json_string(qtbot):
    editor = QPlainTextEdit()
    qtbot.addWidget(editor)
    editor.setPlainText('{"hello": 12}')
    highlighter = highlighter_for(".json", editor.document())
    assert isinstance(highlighter, JsonHighlighter)
    highlighter.rehighlight()
    colors = _layout_foregrounds(editor.document())
    assert (1, 7, "#0f766e") in colors
    assert (10, 2, "#c2410c") in colors


def test_highlighter_colors_c_keyword_number_and_comment(qtbot):
    editor = QPlainTextEdit()
    qtbot.addWidget(editor)
    editor.setPlainText("int x = 12; // done")
    header = QPlainTextEdit()
    qtbot.addWidget(header)
    header.setPlainText("#include \"foo.h\"")
    highlighter = highlighter_for(".c", editor.document())
    header_hl = highlighter_for(".h", header.document())
    assert isinstance(highlighter, CHighlighter)
    assert isinstance(header_hl, CHighlighter)
    highlighter.rehighlight()
    header_hl.rehighlight()
    colors = _layout_foregrounds(editor.document())
    assert (0, 3, COBALT.lower()) in colors
    assert (8, 2, "#c2410c") in colors
    comment_colors = {color for _start, _length, color in colors}
    assert MUTED.lower() in comment_colors
    include_colors = {
        color for _start, _length, color in _layout_foregrounds(header.document())
    }
    assert COBALT.lower() in include_colors
    assert "#0f766e" in include_colors


def test_highlighter_colors_yaml_key_and_xml_tag(qtbot):
    yaml_editor = QPlainTextEdit()
    xml_editor = QPlainTextEdit()
    qtbot.addWidget(yaml_editor)
    qtbot.addWidget(xml_editor)
    yaml_editor.setPlainText('name: "ok"')
    xml_editor.setPlainText('<root attr="x"/>')
    yaml_hl = highlighter_for(".yml", yaml_editor.document())
    xml_hl = highlighter_for(".xml", xml_editor.document())
    assert isinstance(yaml_hl, YamlHighlighter)
    assert isinstance(xml_hl, XmlHighlighter)
    yaml_hl.rehighlight()
    xml_hl.rehighlight()
    yaml_colors = {color for _start, _length, color in _layout_foregrounds(yaml_editor.document())}
    xml_colors = {color for _start, _length, color in _layout_foregrounds(xml_editor.document())}
    assert COBALT.lower() in yaml_colors
    assert "#0f766e" in yaml_colors
    assert COBALT.lower() in xml_colors
    assert "#0f766e" in xml_colors


def test_code_view_is_readonly_with_gutter(qtbot, tmp_path: Path):
    path = tmp_path / "data.json"
    path.write_text("{\n  \"a\": 1\n}\n", encoding="utf-8")
    view = CodeTextView()
    qtbot.addWidget(view)
    view.load_path(path)
    view.show()
    qtbot.waitExposed(view)

    editor = view.editor()
    gutter = view.line_number_area()
    assert editor.isReadOnly() is True
    assert editor.toPlainText().startswith("{")
    assert editor.blockCount() >= 3
    assert gutter is not None
    assert gutter.width() >= 16
    ten_lines = "\n".join(str(i) for i in range(1, 12))
    view.load_text(ten_lines, ".yaml")
    wider = view.line_number_area_width()
    view.load_text("only\n", ".yml")
    narrower = view.line_number_area_width()
    assert wider >= narrower
    assert view.highlighter() is not None
    sheet = editor.styleSheet().replace(" ", "").lower()
    assert PAPER.lower() in sheet
