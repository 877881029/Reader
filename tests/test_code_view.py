from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QPushButton, QSpinBox

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


def test_cpp_suffix_family_uses_c_highlighter(qtbot):
    for suffix in (".cpp", ".hpp", ".cc", ".cxx", ".hh", ".hxx", ".inl", ".ipp"):
        editor = QPlainTextEdit()
        qtbot.addWidget(editor)
        editor.setPlainText("class Reader final {};")
        highlighter = highlighter_for(suffix, editor.document())
        assert isinstance(highlighter, CHighlighter)


def test_highlighter_txt_is_plain_not_json(qtbot):
    editor = QPlainTextEdit()
    qtbot.addWidget(editor)
    editor.setPlainText('{"hello": 12}')
    highlighter = highlighter_for(".txt", editor.document())
    assert highlighter.__class__.__name__ == "PlainHighlighter"
    assert not isinstance(highlighter, JsonHighlighter)
    highlighter.rehighlight()
    colors = _layout_foregrounds(editor.document())
    assert (1, 7, "#0f766e") not in colors


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


def test_code_view_load_path_is_editable_with_gutter(qtbot, tmp_path: Path):
    path = tmp_path / "data.json"
    path.write_text("{\n  \"a\": 1\n}\n", encoding="utf-8")
    view = CodeTextView()
    qtbot.addWidget(view)
    view.load_path(path)
    view.show()
    qtbot.waitExposed(view)

    editor = view.editor()
    gutter = view.line_number_area()
    assert editor.isReadOnly() is False
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


def test_code_view_exposes_named_reading_controls(qtbot):
    view = CodeTextView()
    qtbot.addWidget(view)
    view.load_text("one\ntwo\nthree", ".cpp")

    line_spin = view.findChild(QSpinBox, "codeLineSpin")
    jump_button = view.findChild(QPushButton, "codeLineJump")
    wrap_button = view.findChild(QPushButton, "codeWrapToggle")
    font_decrease = view.findChild(QPushButton, "codeFontDecrease")
    font_increase = view.findChild(QPushButton, "codeFontIncrease")
    font_label = view.findChild(QLabel, "codeFontSize")
    position_label = view.findChild(QLabel, "codeCursorPosition")

    assert view.editor().isReadOnly()
    assert line_spin is not None
    assert jump_button is not None
    assert wrap_button is not None and wrap_button.isCheckable()
    assert font_decrease is not None
    assert font_increase is not None
    assert font_label is not None and font_label.text() == "12 pt"
    assert position_label is not None and position_label.text() == "行 1，列 1"


def test_code_view_line_jump_clamps_and_updates_position(qtbot):
    view = CodeTextView()
    qtbot.addWidget(view)
    view.load_text("one\ntwo\nthree", ".cpp")
    line_spin = view.findChild(QSpinBox, "codeLineSpin")
    jump_button = view.findChild(QPushButton, "codeLineJump")
    position_label = view.findChild(QLabel, "codeCursorPosition")
    assert line_spin is not None
    assert jump_button is not None
    assert position_label is not None

    assert (line_spin.minimum(), line_spin.maximum()) == (1, 3)
    line_spin.setValue(99)
    qtbot.mouseClick(jump_button, Qt.MouseButton.LeftButton)
    assert view.editor().textCursor().blockNumber() == 2
    assert view.editor().textCursor().positionInBlock() == 0
    assert position_label.text() == "行 3，列 1"

    view.editor().moveCursor(QTextCursor.MoveOperation.EndOfBlock)
    assert position_label.text() == "行 3，列 6"


def test_code_view_wrap_and_font_controls_are_bounded(qtbot):
    view = CodeTextView()
    qtbot.addWidget(view)
    view.load_text("\n".join(str(index) for index in range(100)), ".cpp")
    editor = view.editor()
    wrap_button = view.findChild(QPushButton, "codeWrapToggle")
    font_decrease = view.findChild(QPushButton, "codeFontDecrease")
    font_increase = view.findChild(QPushButton, "codeFontIncrease")
    font_label = view.findChild(QLabel, "codeFontSize")
    assert wrap_button is not None
    assert font_decrease is not None
    assert font_increase is not None
    assert font_label is not None

    assert editor.lineWrapMode() == QPlainTextEdit.LineWrapMode.NoWrap
    qtbot.mouseClick(wrap_button, Qt.MouseButton.LeftButton)
    assert editor.lineWrapMode() == QPlainTextEdit.LineWrapMode.WidgetWidth

    initial_tab_stop = editor.tabStopDistance()
    for _ in range(20):
        qtbot.mouseClick(font_increase, Qt.MouseButton.LeftButton)
    wide_gutter = view.line_number_area_width()
    assert editor.font().pointSize() == 24
    assert font_label.text() == "24 pt"
    assert editor.tabStopDistance() > initial_tab_stop

    for _ in range(30):
        qtbot.mouseClick(font_decrease, Qt.MouseButton.LeftButton)
    assert editor.font().pointSize() == 8
    assert font_label.text() == "8 pt"
    assert view.line_number_area_width() < wide_gutter


def test_code_view_loading_resets_navigation_without_losing_highlighter(qtbot):
    view = CodeTextView()
    qtbot.addWidget(view)
    view.load_text("one\ntwo\nthree", ".cpp")
    line_spin = view.findChild(QSpinBox, "codeLineSpin")
    jump_button = view.findChild(QPushButton, "codeLineJump")
    position_label = view.findChild(QLabel, "codeCursorPosition")
    assert line_spin is not None
    assert jump_button is not None
    assert position_label is not None
    line_spin.setValue(3)
    qtbot.mouseClick(jump_button, Qt.MouseButton.LeftButton)

    view.load_text("only", ".yaml")

    assert (line_spin.minimum(), line_spin.maximum(), line_spin.value()) == (1, 1, 1)
    assert position_label.text() == "行 1，列 1"
    assert isinstance(view.highlighter(), YamlHighlighter)


# --- P1 editing -------------------------------------------------------------


def _type(qtbot, view, text: str) -> None:
    editor = view.editor()
    editor.setFocus()
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    editor.setTextCursor(cursor)
    qtbot.keyClicks(editor, text)


def test_load_path_starts_clean_without_undo_history(qtbot, tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("hello\n", encoding="utf-8")
    view = CodeTextView()
    qtbot.addWidget(view)

    view.load_path(path)

    assert view.dirty is False
    assert view.editor().document().isUndoAvailable() is False
    assert view.display_title() == "notes.txt"


def test_typing_marks_dirty_and_undo_restores_clean(qtbot, tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("hello", encoding="utf-8")
    view = CodeTextView()
    qtbot.addWidget(view)
    view.load_path(path)
    seen: list[bool] = []
    view.dirty_changed.connect(seen.append)

    _type(qtbot, view, "!")

    assert view.dirty is True
    assert view.display_title() == "*notes.txt"
    view.editor().undo()
    assert view.dirty is False
    assert seen == [True, False]


@pytest.mark.parametrize(
    ("name", "raw", "expected"),
    [
        ("a.txt", "第一\r\n".encode("gb18030"), "第一!\r\n".encode("gb18030")),
        ("a.json", b'\xef\xbb\xbf{"a":1}\r\n', b'\xef\xbb\xbf{"a":1}\r\n!'),
        ("a.yaml", b"k: v\n", b"k: v\n!"),
    ],
)
def test_save_preserves_encoding_and_newlines(qtbot, tmp_path: Path, name, raw, expected):
    path = tmp_path / name
    path.write_bytes(raw)
    view = CodeTextView()
    qtbot.addWidget(view)
    view.load_path(path)
    if name == "a.txt":
        cursor = view.editor().textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        view.editor().setTextCursor(cursor)
        qtbot.keyClicks(view.editor(), "!")
    else:
        _type(qtbot, view, "!")

    assert view.save() is True

    assert path.read_bytes() == expected
    assert view.dirty is False
    assert view.display_title() == name


def test_save_as_moves_path_and_rehighlights(qtbot, tmp_path: Path):
    source = tmp_path / "a.txt"
    source.write_bytes(b"int x = 1;\n")
    target = tmp_path / "b.cpp"
    view = CodeTextView()
    qtbot.addWidget(view)
    view.load_path(source)
    paths: list[object] = []
    view.path_changed.connect(paths.append)

    view.save_as(target)

    assert target.read_bytes() == b"int x = 1;\n"
    assert view.path == target.resolve()
    assert paths == [target.resolve()]
    assert isinstance(view.highlighter(), CHighlighter)
    assert view.display_title() == "b.cpp"


def test_untitled_text_is_editable_and_cannot_save_without_path(qtbot):
    view = CodeTextView()
    qtbot.addWidget(view)

    view.load_untitled(".txt")
    _type(qtbot, view, "draft")

    assert view.path is None
    assert view.editor().isReadOnly() is False
    assert view.display_title() == "*未命名.txt"
    assert view.save() is False
    assert view.suffix == ".txt"


def test_untitled_save_as_uses_utf8_crlf(qtbot, tmp_path: Path):
    view = CodeTextView()
    qtbot.addWidget(view)
    view.load_untitled(".txt")
    _type(qtbot, view, "a")
    view.editor().insertPlainText("\nb")
    target = tmp_path / "new.txt"

    view.save_as(target)

    assert target.read_bytes() == b"a\r\nb"


def test_lossy_file_opens_read_only_with_notice(qtbot, tmp_path: Path):
    path = tmp_path / "bin.txt"
    path.write_bytes(b"ok \x80\x81\xfe\xff\xff")
    view = CodeTextView()
    qtbot.addWidget(view)

    view.load_path(path)

    notice = view.findChild(QLabel, "codeReadOnlyNotice")
    assert view.editor().isReadOnly() is True
    assert notice is not None and notice.text() == "只读：无法无损识别编码"
    assert notice.isHidden() is False
    assert view.save() is False
    assert path.read_bytes() == b"ok \x80\x81\xfe\xff\xff"
