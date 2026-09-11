from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, QSize
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from reader.preview.graphic_view import GraphicView
from reader.theme import PAPER


class ImageView(GraphicView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("imageView")
        self.setStyleSheet(f"QWidget#imageView {{ background: {PAPER}; }}")
        self._pixmap = QPixmap()
        self._valid = False

    def is_valid(self) -> bool:
        return self._valid

    def error_message(self) -> str:
        return "无法打开此图片"

    def intrinsic_size(self) -> QSize:
        return self._pixmap.size()

    def load_path(self, path: Path) -> None:
        pixmap = QPixmap()
        self._valid = pixmap.load(str(path)) and not pixmap.isNull()
        self._pixmap = pixmap if self._valid else QPixmap()
        self.reset_view()

    def paint_graphic(self, painter: QPainter, dest: QRectF) -> None:
        painter.drawPixmap(dest, self._pixmap, QRectF(self._pixmap.rect()))
