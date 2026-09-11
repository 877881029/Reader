from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget

from reader.theme import INK, PAPER


class SvgView(QWidget):
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

    def load_path(self, path: Path) -> None:
        payload = Path(path).read_bytes()
        try:
            self._source = payload.decode("utf-8")
        except UnicodeDecodeError:
            self._source = payload.decode("utf-8", errors="replace")
        self._valid = self._renderer.load(QByteArray(payload)) and self._renderer.isValid()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(PAPER))
        if not self._valid:
            painter.setPen(QColor(INK))
            painter.drawText(
                self.rect(),
                int(Qt.AlignmentFlag.AlignCenter),
                "无法渲染此 SVG",
            )
            return
        view = QRectF(self.rect()).adjusted(24, 24, -24, -24)
        default = self._renderer.defaultSize()
        if default.width() <= 0 or default.height() <= 0 or view.width() <= 0 or view.height() <= 0:
            self._renderer.render(painter, view)
            return
        scale = min(view.width() / default.width(), view.height() / default.height())
        width = default.width() * scale
        height = default.height() * scale
        dest = QRectF(
            view.center().x() - width / 2,
            view.center().y() - height / 2,
            width,
            height,
        )
        self._renderer.render(painter, dest)
