from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
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
