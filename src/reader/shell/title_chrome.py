from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTabBar,
    QToolButton,
    QWidget,
)


class TitleChrome(QWidget):
    """Single-row Notepad-like chrome: icon | tabs | + | caption | buttons."""

    minimize_requested = Signal()
    maximize_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("titleChrome")
        self.setFixedHeight(36)

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
                background: #f3f3f3;
                border-bottom: 1px solid #e0e0e0;
            }
            QTabBar::tab {
                background: transparent;
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
                background: #e8e8e8;
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

    def update_maximize_state(self, is_maximized: bool) -> None:
        if is_maximized:
            self._max_button.setText("❐")
            self._max_button.setToolTip("还原")
        else:
            self._max_button.setText("□")
            self._max_button.setToolTip("最大化")
