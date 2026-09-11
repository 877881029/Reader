from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, QSize
from PySide6.QtGui import QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget

from reader.preview.graphic_view import GraphicView
from reader.theme import PAPER


class SvgView(GraphicView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("svgView")
        self.setStyleSheet(f"QWidget#svgView {{ background: {PAPER}; }}")
        self._renderer = QSvgRenderer(self)
        self._source = ""
        self._valid = False

    def is_valid(self) -> bool:
        return self._valid

    def text(self) -> str:
        return self._source

    def error_message(self) -> str:
        return "无法渲染此 SVG"

    def intrinsic_size(self) -> QSize:
        return self._renderer.defaultSize()

    def load_path(self, path: Path) -> None:
        payload = Path(path).read_bytes()
        try:
            self._source = payload.decode("utf-8")
        except UnicodeDecodeError:
            self._source = payload.decode("utf-8", errors="replace")
        self._valid = self._renderer.load(QByteArray(payload)) and self._renderer.isValid()
        self.reset_view()

    def paint_graphic(self, painter: QPainter, dest: QRectF) -> None:
        self._renderer.render(painter, dest)
