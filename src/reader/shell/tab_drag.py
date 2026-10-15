"""Tab bar whose tabs can be dragged out of the window (Chrome/Notepad style)."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QLabel, QTabBar, QWidget

# How far (px) the pointer must leave the strip vertically before a tab detaches.
DETACH_MARGIN = 24


class ReaderTabBar(QTabBar):
    """Reports a tab dragged off the strip; the window decides where it lands."""

    detach_finished = Signal(int, QPoint)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._press_index = -1
        self._grab_offset = QPoint()
        self._detaching = False
        self._ghost: QLabel | None = None

    def is_detaching(self) -> bool:
        return self._detaching

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            self._press_index = self.tabAt(pos)
            if self._press_index >= 0:
                self._grab_offset = pos - self.tabRect(self._press_index).topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        global_pos = event.globalPosition().toPoint()
        if self._detaching:
            self._move_ghost(global_pos)
            return
        if (
            self._press_index >= 0
            and event.buttons() & Qt.MouseButton.LeftButton
            and self._left_strip(event.position().toPoint())
        ):
            self._begin_detach(global_pos)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt API
        if self._detaching and event.button() == Qt.MouseButton.LeftButton:
            index = self._press_index
            self._end_detach()
            self.detach_finished.emit(index, event.globalPosition().toPoint())
            return
        self._press_index = -1
        super().mouseReleaseEvent(event)

    def _left_strip(self, pos: QPoint) -> bool:
        return pos.y() < -DETACH_MARGIN or pos.y() > self.height() + DETACH_MARGIN

    def _begin_detach(self, global_pos: QPoint) -> None:
        self._detaching = True
        ghost = QLabel(
            None,
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput,
        )
        ghost.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        ghost.setPixmap(self.grab(self.tabRect(self._press_index)))
        ghost.setWindowOpacity(0.85)
        ghost.adjustSize()
        self._ghost = ghost
        self._move_ghost(global_pos)
        ghost.show()
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _move_ghost(self, global_pos: QPoint) -> None:
        if self._ghost is not None:
            self._ghost.move(global_pos - self._grab_offset)

    def _end_detach(self) -> None:
        self._detaching = False
        self._press_index = -1
        self.unsetCursor()
        ghost, self._ghost = self._ghost, None
        if ghost is not None:
            ghost.hide()
            ghost.deleteLater()
