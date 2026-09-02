from __future__ import annotations

import ctypes
import os
from collections.abc import Callable

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

BORDER_PX = 8
WM_NCLBUTTONDOWN = 0x00A1
_INTERACTIVE_CHROME = {
    "tabNewButton",
    "titleMinButton",
    "titleMaxButton",
    "titleCloseButton",
}


def begin_window_move(widget: QWidget) -> bool:
    """Start a native move. WM_NCHITTEST alone is swallowed on frameless Qt windows."""
    window = widget.window()
    handle = window.windowHandle()
    if handle is not None:
        try:
            if handle.startSystemMove():
                return True
        except Exception:
            pass
    if os.name == "nt":
        hwnd = int(window.winId())
        if hwnd:
            ctypes.windll.user32.ReleaseCapture()
            ctypes.windll.user32.SendMessageW(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0)
            return True
    return False


def _contains_global(widget: QWidget | None, global_pos: QPoint) -> bool:
    if widget is None or not widget.isVisible():
        return False
    top_left = widget.mapToGlobal(QPoint(0, 0))
    return QRect(top_left, widget.size()).contains(global_pos)


def hit_test_for_window(window: QMainWindow, global_pos: QPoint) -> int:
    """Map a screen point to a Win32 HT* code for frameless chrome."""
    local = window.mapFromGlobal(global_pos)
    width = window.width()
    height = window.height()
    border = BORDER_PX
    maximized = window.isMaximized()

    if not maximized:
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
        if bottom:
            return HTBOTTOM
        # Top edge resize only outside the custom title chrome height so the
        # chrome row itself remains draggable (HTCAPTION) like Notepad.
        chrome = window.findChild(QWidget, "titleChrome")
        chrome_bottom = chrome.height() if chrome is not None else 0
        if top and local.y() < border and local.y() >= chrome_bottom:
            return HTTOP
        if top and chrome is None:
            return HTTOP

    if _contains_global(window.findChild(QWidget, "titleMinButton"), global_pos):
        return HTMINBUTTON
    if _contains_global(window.findChild(QWidget, "titleMaxButton"), global_pos):
        return HTMAXBUTTON
    if _contains_global(window.findChild(QWidget, "titleCloseButton"), global_pos):
        return HTCLOSE

    tab_bar = None
    tabs = getattr(window, "_tabs", None)
    if tabs is not None:
        tab_bar = tabs.tabBar()
    if _contains_global(tab_bar, global_pos):
        return HTCLIENT
    if _contains_global(window.findChild(QWidget, "tabNewButton"), global_pos):
        return HTCLIENT

    chrome = window.findChild(QWidget, "titleChrome")
    if _contains_global(chrome, global_pos):
        return HTCAPTION
    return HTCLIENT


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
        self._min_button.setFixedSize(46, 32)
        self._min_button.setToolTip("最小化")
        self._min_button.clicked.connect(self.minimize_requested.emit)
        row.addWidget(self._min_button, 0, Qt.AlignmentFlag.AlignVCenter)

        self._max_button = QToolButton(self)
        self._max_button.setObjectName("titleMaxButton")
        self._max_button.setText("□")
        self._max_button.setAutoRaise(True)
        self._max_button.setFixedSize(46, 32)
        self._max_button.setToolTip("最大化")
        self._max_button.clicked.connect(self.maximize_requested.emit)
        row.addWidget(self._max_button, 0, Qt.AlignmentFlag.AlignVCenter)

        self._close_button = QToolButton(self)
        self._close_button.setObjectName("titleCloseButton")
        self._close_button.setText("✕")
        self._close_button.setAutoRaise(True)
        self._close_button.setFixedSize(46, 32)
        self._close_button.setToolTip("关闭")
        self._close_button.clicked.connect(self.close_requested.emit)
        row.addWidget(self._close_button, 0, Qt.AlignmentFlag.AlignVCenter)

        self.setStyleSheet(
            """
            QWidget#titleChrome {
                background: #ffffff;
                border-bottom: none;
            }
            QTabBar::tab {
                background: #f3f3f3;
                border: none;
                padding: 6px 12px;
                margin: 4px 2px;
                border-radius: 6px;
                color: #222;
            }
            QTabBar::tab:selected {
                background: #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background: #ececec;
            }
            QToolButton#tabNewButton {
                padding: 2px 8px;
                border: none;
                border-radius: 4px;
                font-size: 16px;
            }
            QToolButton#tabNewButton:hover {
                background: #e0e0e0;
            }
            QToolButton#titleMinButton,
            QToolButton#titleMaxButton,
            QToolButton#titleCloseButton {
                border: none;
                border-radius: 0;
                font-size: 12px;
                color: #222;
            }
            QToolButton#titleMinButton:hover,
            QToolButton#titleMaxButton:hover {
                background: #e5e5e5;
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
