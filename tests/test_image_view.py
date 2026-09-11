from pathlib import Path

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QLabel, QPushButton, QSlider

from reader.theme import PAPER


def _write_png(path: Path) -> None:
    image = QImage(16, 16, QImage.Format.Format_RGB32)
    image.fill(QColor("#2563eb"))
    assert image.save(str(path), "PNG")


def test_image_view_renders_png_and_rejects_garbage(qtbot, tmp_path: Path):
    from reader.preview.image_view import ImageView

    valid = tmp_path / "ok.png"
    _write_png(valid)
    view = ImageView()
    qtbot.addWidget(view)
    view.load_path(valid)
    view.show()
    qtbot.waitExposed(view)

    assert view.is_valid() is True
    assert view.objectName() == "imageView"
    sheet = view.styleSheet().replace(" ", "").lower()
    assert PAPER.lower() in sheet
    assert view.zoom() == 1.0
    assert view.findChildren(QSlider) == []
    assert view.findChildren(QPushButton) == []
    assert view.findChildren(QLabel) == []

    broken = tmp_path / "bad.png"
    broken.write_bytes(b"not an image")
    view.load_path(broken)
    assert view.is_valid() is False
