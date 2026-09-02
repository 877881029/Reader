from __future__ import annotations

import ctypes
import os
from collections.abc import Callable
from ctypes import wintypes

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QTabBar,
    QToolButton,
    QWidget,
)

HTCLIENT = 1
HTCAPTION = 2
HTMINBUTTON = 8
HTMAXBUTTON = 9
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17
HTCLOSE = 20

RESIZE_BORDER_PX = 4
_INTERACTIVE_CHROME = {
    "tabNewButton",
    "titleMinButton",
    "titleMaxButton",
    "titleCloseButton",
}


def begin_window_move(widget: QWidget) -> bool:
    """Move the top-level window. Never use HTCAPTION/WM_NCLBUTTONDOWN — those eat later clicks."""
    window = widget.window()
    if os.name == "nt":
        ctypes.windll.user32.ReleaseCapture()
    handle = window.windowHandle()
    if handle is None:
        return False
    try:
        return bool(handle.startSystemMove())
    except Exception:
        return False


def lparam_to_local(window: QWidget, x: int, y: int) -> QPoint:
    """WM_NCHITTEST lParam is native screen pixels; widgets use logical local pixels."""
    hwnd = int(window.winId())
    point = wintypes.POINT(int(x), int(y))
    ctypes.windll.user32.ScreenToClient(hwnd, ctypes.byref(point))
    dpr = float(window.devicePixelRatioF())
    if dpr <= 0:
        dpr = 1.0
    return QPoint(round(point.x / dpr), round(point.y / dpr))


def _contains_local(window: QWidget, widget: QWidget | None, local: QPoint) -> bool:
    if widget is None or not widget.isVisible():
        return False
    top_left = widget.mapTo(window, QPoint(0, 0))
    return QRect(top_left, widget.size()).contains(local)


def _interactive_chrome_at(window: QMainWindow, local: QPoint) -> bool:
    for name in _INTERACTIVE_CHROME:
        if _contains_local(window, window.findChild(QWidget, name), local):
            return True
    tabs = getattr(window, "_tabs", None)
    if tabs is not None and _contains_local(window, tabs.tabBar(), local):
        return True
    return False


def hit_test_local(window: QMainWindow, local: QPoint) -> int:
    """Qt chrome is always HTCLIENT. Only an empty 4px frame reports resize."""
    if not window.isMaximized() and not _interactive_chrome_at(window, local):
        width = window.width()
        height = window.height()
        border = RESIZE_BORDER_PX
        left = local.x() < border
        right = local.x() >= width - border
        top = local.y() < border
        bottom = local.y() >= height - border
        if top and left:
            return HTTOPLEFT
        if top and right:
            return HTTOPRIGHT
        if bottom and left:
            return HTBOTTOMLEFT
        if bottom and right:
            return HTBOTTOMRIGHT
        if left:
            return HTLEFT
        if right:
            return HTRIGHT
        if top:
            return HTTOP
        if bottom:
            return HTBOTTOM
    return HTCLIENT


def hit_test_for_window(window: QMainWindow, global_pos: QPoint) -> int:
    return hit_test_local(window, window.mapFromGlobal(global_pos))


class TitleChrome(QWidget):
    """Single-row Notepad-like chrome: icon | tabs | + | caption | buttons."""

    minimize_requested = Signal()
    maximize_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("titleChrome")
        self.setFixedHeight(36)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 0, 0, 0)
        row.setSpacing(4)

        self._icon = QLabel(self)
        self._icon.setObjectName("titleAppIcon")
        self._icon.setFixedSize(16, 16)
        self._icon.setScaledContents(True)
        row.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignVCenter)

        self._tab_host = QWidget(self)
        self._tab_host.setObjectName("titleTabHost")
        self._tab_host_layout = QHBoxLayout(self._tab_host)
        self._tab_host_layout.setContentsMargins(0, 0, 0, 0)
        self._tab_host_layout.setSpacing(0)
        row.addWidget(self._tab_host, 0, Qt.AlignmentFlag.AlignVCenter)

        self._plus = QToolButton(self)
        self._plus.setObjectName("tabNewButton")
        self._plus.setText("+")
        self._plus.setAutoRaise(True)
        self._plus.setToolTip("新建标签")
        row.addWidget(self._plus, 0, Qt.AlignmentFlag.AlignVCenter)

        self._caption = QWidget(self)
        self._caption.setObjectName("titleCaption")
        self._caption.setMinimumWidth(24)
        row.addWidget(self._caption, 1)
        self._icon.installEventFilter(self)
        self._caption.installEventFilter(self)

        self._min_button = QToolButton(self)
        self._min_button.setObjectName("titleMinButton")
        self._min_button.setText("─")
        self._min_button.setAutoRaise(True)
        self._min_button.setFixedSize(46, 36)
        self._min_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._min_button.setToolTip("最小化")
        self._min_button.clicked.connect(self.minimize_requested.emit)
        row.addWidget(self._min_button, 0, Qt.AlignmentFlag.AlignTop)

        self._max_button = QToolButton(self)
        self._max_button.setObjectName("titleMaxButton")
        self._max_button.setText("□")
        self._max_button.setAutoRaise(True)
        self._max_button.setFixedSize(46, 36)
        self._max_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._max_button.setToolTip("最大化")
        self._max_button.clicked.connect(self.maximize_requested.emit)
        row.addWidget(self._max_button, 0, Qt.AlignmentFlag.AlignTop)

        self._close_button = QToolButton(self)
        self._close_button.setObjectName("titleCloseButton")
        self._close_button.setText("✕")
        self._close_button.setAutoRaise(True)
        self._close_button.setFixedSize(46, 36)
        self._close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._close_button.setToolTip("关闭")
        self._close_button.clicked.connect(self.close_requested.emit)
        row.addWidget(self._close_button, 0, Qt.AlignmentFlag.AlignTop)

        self.setStyleSheet(
            """
            QWidget#titleChrome {
                background: #f3f3f3;
                border-bottom: none;
            }
            QWidget#titleCaption,
            QWidget#titleTabHost,
            QLabel#titleAppIcon {
                background: transparent;
            }
            QTabBar {
                background: transparent;
                border: none;
            }
            QTabBar::tab {
                background: transparent;
                border: none;
                padding: 6px 12px;
                margin: 4px 2px 0 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border-bottom-left-radius: 0;
                border-bottom-right-radius: 0;
                color: #222;
            }
            QTabBar::tab:selected {
                background: #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background: #e8e8e8;
            }
            QToolButton#tabNewButton {
                background: transparent;
                padding: 2px 8px;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                color: #222;
            }
            QToolButton#tabNewButton:hover {
                background: #e5e5e5;
            }
            QToolButton#titleMinButton,
            QToolButton#titleMaxButton,
            QToolButton#titleCloseButton {
                background: #f3f3f3;
                border: none;
                border-radius: 0;
                padding: 0;
                font-size: 12px;
                color: #222;
            }
            QToolButton#titleMinButton:hover,
            QToolButton#titleMaxButton:hover {
                background: #e5e5e5;
            }
            QToolButton#titleMinButton:pressed,
            QToolButton#titleMaxButton:pressed {
                background: #dcdcdc;
            }
            QToolButton#titleCloseButton:hover {
                background: #e81123;
                color: #ffffff;
            }
            """
        )

    def set_window_icon(self, icon: QIcon) -> None:
        if icon.isNull():
            return
        self._icon.setPixmap(icon.pixmap(16, 16))

    def adopt_tab_bar(self, tab_bar: QTabBar) -> None:
        tab_bar.setExpanding(False)
        tab_bar.setUsesScrollButtons(True)
        tab_bar.setDrawBase(False)
        tab_bar.setParent(self._tab_host)
        self._tab_host_layout.addWidget(tab_bar)
        tab_bar.show()
        self._tab_host.adjustSize()

    def set_plus_handler(self, callback: Callable[[], None]) -> None:
        self._plus.clicked.connect(callback)

    def eventFilter(self, watched, event: QEvent) -> bool:  # noqa: N802
        if watched in {self._icon, self._caption}:
            if (
                event.type() == QEvent.Type.MouseButtonPress
                and isinstance(event, QMouseEvent)
                and event.button() == Qt.MouseButton.LeftButton
            ):
                begin_window_move(self.window())
                return True
            if (
                event.type() == QEvent.Type.MouseButtonDblClick
                and isinstance(event, QMouseEvent)
                and event.button() == Qt.MouseButton.LeftButton
            ):
                self._toggle_parent_maximize()
                return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if self._is_caption_handle(child):
                begin_window_move(self.window())
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if self._is_caption_handle(child):
                self._toggle_parent_maximize()
                return
        super().mouseDoubleClickEvent(event)

    def _is_caption_handle(self, child: QWidget | None) -> bool:
        widget: QWidget | None = child
        if widget is None:
            return True
        while widget is not None:
            name = widget.objectName()
            if name in _INTERACTIVE_CHROME:
                return False
            if isinstance(widget, QTabBar):
                return False
            if name in {"titleAppIcon", "titleCaption"} or widget is self:
                return True
            widget = widget.parentWidget()
        return True

    def _toggle_parent_maximize(self) -> None:
        window = self.window()
        if window.isMaximized():
            window.showNormal()
        else:
            window.showMaximized()

    def update_maximize_state(self, is_maximized: bool) -> None:
        if is_maximized:
            self._max_button.setText("❐")
            self._max_button.setToolTip("还原")
        else:
            self._max_button.setText("□")
            self._max_button.setToolTip("最大化")
