from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QToolButton, QWidget

from reader.theme import CARD, CHROME, INK, LINE, MUTED


class GotoLineBar(QWidget):
    """Ctrl+J bar shown in the same place and style as the find bar."""

    submitted = Signal(str)
    hide_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("goToLineBar")
        self.setStyleSheet(
            f"""
            #goToLineBar {{
                background: {CHROME};
                border-bottom: 1px solid {LINE};
            }}
            QLineEdit#goToLineInput {{
                background: {CARD};
                color: {INK};
                border: 1px solid {LINE};
                padding: 4px 8px;
                border-radius: 4px;
            }}
            QLabel#goToLineMessage {{ color: {MUTED}; }}
            QToolButton {{ color: {INK}; border: none; padding: 4px 8px; }}
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        self._input = QLineEdit(self)
        self._input.setObjectName("goToLineInput")
        self._input.installEventFilter(self)

        self._message = QLabel("", self)
        self._message.setObjectName("goToLineMessage")
        self._message.hide()

        close = QToolButton(self)
        close.setObjectName("goToLineClose")
        close.setText("×")
        close.setToolTip("关闭")
        close.clicked.connect(self.hide_requested.emit)

        layout.addWidget(self._input, 1)
        layout.addWidget(self._message)
        layout.addWidget(close)
        self.hide()

    def input_edit(self) -> QLineEdit:
        return self._input

    def open(self, maximum: int) -> None:
        self._input.setPlaceholderText(f"转到行（1–{maximum}）")
        self._input.clear()
        self.set_message("")
        self.show()
        self._input.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def set_message(self, text: str) -> None:
        self._message.setText(text)
        self._message.setVisible(bool(text))

    def eventFilter(self, watched, event: QEvent) -> bool:  # noqa: N802
        if watched is self._input and event.type() == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
            if event.key() == Qt.Key.Key_Escape:
                self.hide_requested.emit()
                return True
            if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
                self.submitted.emit(self._input.text())
                return True
        return super().eventFilter(watched, event)
