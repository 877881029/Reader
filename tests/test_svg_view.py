from pathlib import Path

from reader.preview.find_support import find_in_widget
from reader.theme import PAPER


_CIRCLE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
    '<circle cx="32" cy="32" r="24" fill="#2563eb"/></svg>'
)


def test_svg_view_renders_valid_and_rejects_garbage(qtbot, tmp_path: Path):
    from reader.preview.svg_view import SvgView

    valid = tmp_path / "ok.svg"
    valid.write_text(_CIRCLE, encoding="utf-8")
    view = SvgView()
    qtbot.addWidget(view)
    view.load_path(valid)
    view.show()
    qtbot.waitExposed(view)

    assert view.is_valid() is True
    assert view.objectName() == "svgView"
    sheet = view.styleSheet().replace(" ", "").lower()
    assert PAPER.lower() in sheet
    assert "circle" in view.text()
    assert find_in_widget(view, "2563eb").found is True
    assert find_in_widget(view, "nope").found is False

    broken = tmp_path / "bad.svg"
    broken.write_text("not an svg", encoding="utf-8")
    view.load_path(broken)
    assert view.is_valid() is False
    assert "not an svg" in view.text()
