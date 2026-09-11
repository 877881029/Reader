from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QSlider

from reader.preview.find_support import find_in_widget
from reader.theme import PAPER


_CIRCLE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
    '<circle cx="32" cy="32" r="24" fill="#2563eb"/></svg>'
)


def _send_wheel(view, delta_y: int, *, ctrl: bool) -> None:
    pos = QPointF(view.rect().center())
    modifiers = (
        Qt.KeyboardModifier.ControlModifier if ctrl else Qt.KeyboardModifier.NoModifier
    )
    event = QWheelEvent(
        pos,
        view.mapToGlobal(pos.toPoint()),
        QPoint(),
        QPoint(0, delta_y),
        Qt.MouseButton.NoButton,
        modifiers,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(view, event)


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


def test_svg_view_zooms_with_ctrl_wheel_only(qtbot, tmp_path: Path):
    from reader.preview.svg_view import SvgView

    path = tmp_path / "ok.svg"
    path.write_text(_CIRCLE, encoding="utf-8")
    view = SvgView()
    qtbot.addWidget(view)
    view.resize(400, 300)
    view.load_path(path)
    view.show()
    qtbot.waitExposed(view)

    assert view.zoom() == 1.0
    assert view.findChildren(QSlider) == []
    assert view.findChildren(QPushButton) == []
    assert view.findChildren(QLabel) == []

    _send_wheel(view, 120, ctrl=False)
    assert view.zoom() == 1.0

    _send_wheel(view, 120, ctrl=True)
    assert view.zoom() > 1.0
    zoomed = view.zoom()
    _send_wheel(view, -120, ctrl=True)
    assert view.zoom() < zoomed
    assert view.zoom() == pytest.approx(1.0)
