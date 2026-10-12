"""Runtime-painted line icons for chrome menus (no asset files needed)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from reader.theme import INK

_Painter = Callable[[QPainter], None]


def _new_file(p: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(4, 2)
    path.lineTo(10, 2)
    path.lineTo(13, 5)
    path.lineTo(13, 14)
    path.lineTo(4, 14)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(10, 2), QPointF(10, 5))
    p.drawLine(QPointF(10, 5), QPointF(13, 5))
    p.drawLine(QPointF(8.5, 7.5), QPointF(8.5, 11.5))
    p.drawLine(QPointF(6.5, 9.5), QPointF(10.5, 9.5))


def _open_file(p: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(2, 13)
    path.lineTo(2, 3.5)
    path.lineTo(6, 3.5)
    path.lineTo(7.5, 5)
    path.lineTo(12.5, 5)
    path.lineTo(12.5, 7)
    p.drawPath(path)
    tray = QPainterPath()
    tray.moveTo(2, 13)
    tray.lineTo(4.5, 7)
    tray.lineTo(14.5, 7)
    tray.lineTo(12, 13)
    tray.closeSubpath()
    p.drawPath(tray)


def _browser(p: QPainter) -> None:
    p.drawEllipse(QRectF(2, 2, 12, 12))
    p.drawEllipse(QRectF(5.5, 2, 5, 12))
    p.drawLine(QPointF(2, 8), QPointF(14, 8))


def _terminal(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(1.5, 2.5, 13, 11), 1.5, 1.5)
    p.drawLine(QPointF(4, 6), QPointF(6.5, 8))
    p.drawLine(QPointF(6.5, 8), QPointF(4, 10))
    p.drawLine(QPointF(8, 10.5), QPointF(11.5, 10.5))


def _paint(draw: _Painter, color: str) -> QIcon:
    icon = QIcon()
    for scale in (1, 2):
        pixmap = QPixmap(16 * scale, 16 * scale)
        pixmap.setDevicePixelRatio(scale)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        draw(painter)
        painter.end()
        icon.addPixmap(pixmap)
    return icon


_ICONS: dict[str, _Painter] = {
    "new_file": _new_file,
    "open_file": _open_file,
    "browser": _browser,
    "terminal": _terminal,
}


def line_icon(name: str, color: str = INK) -> QIcon:
    return _paint(_ICONS[name], color)
