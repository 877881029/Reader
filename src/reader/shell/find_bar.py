from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QWidget,
)

from reader.theme import CARD, CHROME, INK, LINE, MUTED, PAPER


class FindBar(QWidget):
    next_requested = Signal()
    previous_requested = Signal()
    hide_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("findBar")
        self.setStyleSheet(
            f"""
            #findBar {{
                background: {CHROME};
                border-bottom: 1px solid {LINE};
            }}
            QLineEdit#findQuery {{
                background: {CARD};
                color: {INK};
                border: 1px solid {LINE};
                padding: 4px 8px;
                border-radius: 4px;
            }}
            QLabel#findNotFound {{ color: {MUTED}; }}
            QToolButton {{ color: {INK}; border: none; padding: 4px 8px; }}
            QToolButton:checked {{ background: {PAPER}; }}
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        self._query = QLineEdit(self)
        self._query.setObjectName("findQuery")
        self._query.setPlaceholderText("查找")
        self._query.installEventFilter(self)

        self._match_case = QToolButton(self)
        self._match_case.setObjectName("findMatchCase")
        self._match_case.setText("Aa")
        self._match_case.setCheckable(True)
        self._match_case.setToolTip("区分大小写")

        previous = QToolButton(self)
        previous.setObjectName("findPrevious")
        previous.setText("上一个")
        previous.clicked.connect(self.previous_requested.emit)

        nxt = QToolButton(self)
        nxt.setObjectName("findNext")
        nxt.setText("下一个")
        nxt.clicked.connect(self.next_requested.emit)

        self._not_found = QLabel("未找到", self)
        self._not_found.setObjectName("findNotFound")
        self._not_found.hide()

        close = QToolButton(self)
        close.setObjectName("findClose")
        close.setText("×")
        close.setToolTip("关闭")
        close.clicked.connect(self.hide_requested.emit)

        layout.addWidget(self._query, 1)
        layout.addWidget(self._match_case)
        layout.addWidget(previous)
        layout.addWidget(nxt)
        layout.addWidget(self._not_found)
        layout.addWidget(close)
        self.hide()

    def query_edit(self) -> QLineEdit:
        return self._query

    def query(self) -> str:
        return self._query.text()

    def set_query(self, text: str) -> None:
        self._query.setText(text)

    def match_case(self) -> bool:
        return self._match_case.isChecked()

    def set_not_found(self, visible: bool) -> None:
        self._not_found.setVisible(visible)

    def not_found_visible(self) -> bool:
        return self._not_found.isVisible()

    def find_next(self) -> None:
        self.next_requested.emit()

    def find_previous(self) -> None:
        self.previous_requested.emit()

    def focus_query(self) -> None:
        self._query.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self._query.selectAll()

    def eventFilter(self, watched, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
            if event.key() == Qt.Key.Key_Escape:
                self.hide_requested.emit()
                return True
            if watched is self._query and event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.previous_requested.emit()
                else:
                    self.next_requested.emit()
                return True
        return super().eventFilter(watched, event)
