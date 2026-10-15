from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from reader.shell.tab_drag import DETACH_MARGIN, ReaderTabBar


def _send(bar, kind, pos: QPoint, buttons=Qt.MouseButton.LeftButton) -> None:
    button = (
        Qt.MouseButton.NoButton
        if kind == QEvent.Type.MouseMove
        else Qt.MouseButton.LeftButton
    )
    event = QMouseEvent(
        kind,
        QPointF(pos),
        QPointF(bar.mapToGlobal(pos)),
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(bar, event)


def _bar(qtbot) -> ReaderTabBar:
    bar = ReaderTabBar()
    bar.addTab("one")
    bar.addTab("two")
    qtbot.addWidget(bar)
    bar.show()
    qtbot.waitExposed(bar)
    return bar


def test_dragging_a_tab_out_of_the_bar_reports_detach(qtbot):
    bar = _bar(qtbot)
    finished: list[tuple[int, QPoint]] = []
    bar.detach_finished.connect(lambda index, pos: finished.append((index, pos)))
    start = bar.tabRect(1).center()
    outside = QPoint(start.x() + 30, bar.height() + DETACH_MARGIN + 40)

    _send(bar, QEvent.Type.MouseButtonPress, start)
    _send(bar, QEvent.Type.MouseMove, outside)
    assert bar.is_detaching() is True
    _send(bar, QEvent.Type.MouseButtonRelease, outside, Qt.MouseButton.NoButton)

    assert finished == [(1, bar.mapToGlobal(outside))]
    assert bar.is_detaching() is False


def test_small_moves_and_clicks_do_not_detach(qtbot):
    bar = _bar(qtbot)
    finished: list[int] = []
    bar.detach_finished.connect(lambda index, _pos: finished.append(index))
    start = bar.tabRect(1).center()
    near = QPoint(start.x() + 5, bar.height() + DETACH_MARGIN - 4)

    _send(bar, QEvent.Type.MouseButtonPress, start)
    _send(bar, QEvent.Type.MouseMove, near)
    _send(bar, QEvent.Type.MouseButtonRelease, near, Qt.MouseButton.NoButton)

    assert finished == []
    assert bar.currentIndex() == 1


def test_moving_without_a_pressed_tab_never_detaches(qtbot):
    bar = _bar(qtbot)
    finished: list[int] = []
    bar.detach_finished.connect(lambda index, _pos: finished.append(index))
    far = QPoint(10, bar.height() + DETACH_MARGIN + 80)

    _send(bar, QEvent.Type.MouseMove, far)
    _send(bar, QEvent.Type.MouseButtonRelease, far, Qt.MouseButton.NoButton)

    assert finished == []
    assert bar.is_detaching() is False
