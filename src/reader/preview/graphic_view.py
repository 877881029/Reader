from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QWheelEvent
from PySide6.QtWidgets import QWidget

from reader.theme import INK, PAPER

MIN_ZOOM = 0.25
MAX_ZOOM = 16.0
ZOOM_STEP = 1.15
_PAD = 24.0


class GraphicView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self._drag_start: QPointF | None = None
        self._drag_pan = QPointF(0, 0)
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)

    def zoom(self) -> float:
        return self._zoom

    def is_valid(self) -> bool:
        return False

    def intrinsic_size(self) -> QSize:
        return QSize()

    def error_message(self) -> str:
        return "无法打开此文件"

    def paint_graphic(self, painter: QPainter, dest: QRectF) -> None:
        return

    def reset_view(self) -> None:
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self._drag_start = None
        self.update()

    def apply_wheel_zoom(self, angle_delta_y: int, anchor: QPointF) -> None:
        if angle_delta_y == 0 or not self.is_valid():
            return
        steps = angle_delta_y / 120.0
        factor = ZOOM_STEP**steps
        new_zoom = min(MAX_ZOOM, max(MIN_ZOOM, self._zoom * factor))
        if abs(new_zoom - self._zoom) < 1e-9:
            return
        before = self._content_rect()
        if before.width() > 0 and before.height() > 0:
            rel_x = (anchor.x() - before.x()) / before.width()
            rel_y = (anchor.y() - before.y()) / before.height()
        else:
            rel_x = 0.5
            rel_y = 0.5
        self._zoom = new_zoom
        after = self._content_rect()
        self._pan = QPointF(
            self._pan.x() + (anchor.x() - (after.x() + rel_x * after.width())),
            self._pan.y() + (anchor.y() - (after.y() + rel_y * after.height())),
        )
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta == 0:
                delta = event.pixelDelta().y()
            self.apply_wheel_zoom(delta, event.position())
            event.accept()
            return
        event.ignore()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.is_valid():
            self._drag_start = event.position()
            self._drag_pan = QPointF(self._pan)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_start is None:
            super().mouseMoveEvent(event)
            return
        delta = event.position() - self._drag_start
        self._pan = self._drag_pan + delta
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._drag_start is not None and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _viewport(self) -> QRectF:
        return QRectF(self.rect()).adjusted(_PAD, _PAD, -_PAD, -_PAD)

    def _content_rect(self) -> QRectF:
        view = self._viewport()
        size = self.intrinsic_size()
        if size.width() <= 0 or size.height() <= 0 or view.width() <= 0 or view.height() <= 0:
            return view
        fit = min(view.width() / size.width(), view.height() / size.height())
        scale = fit * self._zoom
        width = size.width() * scale
        height = size.height() * scale
        return QRectF(
            view.center().x() - width / 2 + self._pan.x(),
            view.center().y() - height / 2 + self._pan.y(),
            width,
            height,
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor(PAPER))
        if not self.is_valid():
            painter.setPen(QColor(INK))
            painter.drawText(
                self.rect(),
                int(Qt.AlignmentFlag.AlignCenter),
                self.error_message(),
            )
            return
        self.paint_graphic(painter, self._content_rect())
