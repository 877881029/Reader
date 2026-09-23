from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QResizeEvent,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from reader.preview.syntax import highlighter_for
from reader.theme import CHROME, HOVER, INK, LINE, MUTED, PAPER


class _LineNumberArea(QWidget):
    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self.setObjectName("codeLineNumbers")
        self._editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:  # noqa: N802
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("codeTextEditor")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont("Cascadia Code")
        if font.exactMatch() is False:
            font = QFont("Consolas")
        font.setPointSize(12)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.setStyleSheet(
            f"QPlainTextEdit#codeTextEditor {{ background: {PAPER}; border: none; color: {INK}; }}"
        )
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self._gutter = _LineNumberArea(self)
        self.blockCountChanged.connect(self._update_gutter_width)
        self.updateRequest.connect(self._update_gutter)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._update_gutter_width(0)
        self._highlight_current_line()

    def line_number_area(self) -> QWidget:
        return self._gutter

    def line_number_area_width(self) -> int:
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 18 + self.fontMetrics().horizontalAdvance("9") * digits

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        rect = self.contentsRect()
        self._gutter.setGeometry(
            QRect(rect.left(), rect.top(), self.line_number_area_width(), rect.height())
        )

    def paint_line_numbers(self, event) -> None:
        painter = QPainter(self._gutter)
        painter.fillRect(event.rect(), QColor(CHROME))
        painter.setPen(QColor(LINE))
        painter.drawLine(self._gutter.width() - 1, event.rect().top(), self._gutter.width() - 1, event.rect().bottom())
        painter.setFont(self.font())
        current = self.textCursor().blockNumber()
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor(INK if block_number == current else MUTED))
                painter.drawText(
                    0,
                    top,
                    self._gutter.width() - 8,
                    round(self.blockBoundingRect(block).height()),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1
        painter.end()

    def _update_gutter_width(self, _count: int) -> None:
        width = self.line_number_area_width()
        self.setViewportMargins(width, 0, 0, 0)
        rect = self.contentsRect()
        self._gutter.setGeometry(QRect(rect.left(), rect.top(), width, rect.height()))

    def _update_gutter(self, rect: QRect, dy: int) -> None:
        if dy:
            self._gutter.scroll(0, dy)
        else:
            self._gutter.update(0, rect.y(), self._gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_gutter_width(0)

    def _highlight_current_line(self) -> None:
        selection = QTextEdit.ExtraSelection()
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(HOVER))
        fmt.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.format = fmt
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])


class CodeTextView(QWidget):
    MIN_FONT_SIZE = 8
    MAX_FONT_SIZE = 24

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("codeTextView")
        self._path: Path | None = None
        self._highlighter = None
        self._editor = CodeEditor(self)
        self._toolbar = QFrame(self)
        self._toolbar.setObjectName("codeToolbar")
        toolbar_layout = QHBoxLayout(self._toolbar)
        toolbar_layout.setContentsMargins(10, 6, 10, 6)
        toolbar_layout.setSpacing(6)

        line_label = QLabel("行", self._toolbar)
        self._line_spin = QSpinBox(self._toolbar)
        self._line_spin.setObjectName("codeLineSpin")
        self._line_spin.setRange(1, 1)
        self._line_spin.setKeyboardTracking(False)
        self._line_spin.setFixedWidth(72)
        self._jump_button = QPushButton("跳转", self._toolbar)
        self._jump_button.setObjectName("codeLineJump")
        self._wrap_button = QPushButton("换行", self._toolbar)
        self._wrap_button.setObjectName("codeWrapToggle")
        self._wrap_button.setCheckable(True)
        self._font_decrease = QPushButton("A-", self._toolbar)
        self._font_decrease.setObjectName("codeFontDecrease")
        self._font_increase = QPushButton("A+", self._toolbar)
        self._font_increase.setObjectName("codeFontIncrease")
        self._font_size_label = QLabel("12 pt", self._toolbar)
        self._font_size_label.setObjectName("codeFontSize")
        self._position_label = QLabel("行 1，列 1", self._toolbar)
        self._position_label.setObjectName("codeCursorPosition")

        toolbar_layout.addWidget(line_label)
        toolbar_layout.addWidget(self._line_spin)
        toolbar_layout.addWidget(self._jump_button)
        toolbar_layout.addWidget(self._wrap_button)
        toolbar_layout.addWidget(self._font_decrease)
        toolbar_layout.addWidget(self._font_increase)
        toolbar_layout.addWidget(self._font_size_label)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self._position_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._toolbar)
        layout.addWidget(self._editor)
        self.setStyleSheet(
            f"""
            #codeTextView {{ background: {PAPER}; }}
            #codeToolbar {{
                background: {CHROME};
                border-bottom: 1px solid {LINE};
            }}
            #codeToolbar QLabel {{ color: {MUTED}; }}
            #codeToolbar QPushButton {{
                min-height: 24px;
                padding: 0 8px;
                border: 1px solid {LINE};
                border-radius: 4px;
                background: {PAPER};
                color: {INK};
            }}
            #codeToolbar QPushButton:checked {{ background: {HOVER}; }}
            """
        )
        self._jump_button.clicked.connect(self._jump_to_requested_line)
        self._wrap_button.toggled.connect(self._set_wrap_enabled)
        self._font_decrease.clicked.connect(self._decrease_font_size)
        self._font_increase.clicked.connect(self._increase_font_size)
        self._editor.blockCountChanged.connect(self._sync_line_range)
        self._editor.cursorPositionChanged.connect(self._sync_position)
        self._sync_font_controls()

    def editor(self) -> CodeEditor:
        return self._editor

    def line_number_area(self) -> QWidget:
        return self._editor.line_number_area()

    def line_number_area_width(self) -> int:
        return self._editor.line_number_area_width()

    def highlighter(self):
        return self._highlighter

    def _jump_to_requested_line(self) -> None:
        line = max(1, min(self._line_spin.value(), self._editor.blockCount()))
        block = self._editor.document().findBlockByNumber(line - 1)
        cursor = QTextCursor(block)
        self._editor.setTextCursor(cursor)
        self._editor.centerCursor()

    def _set_wrap_enabled(self, enabled: bool) -> None:
        mode = (
            QPlainTextEdit.LineWrapMode.WidgetWidth
            if enabled
            else QPlainTextEdit.LineWrapMode.NoWrap
        )
        self._editor.setLineWrapMode(mode)

    def _decrease_font_size(self) -> None:
        self._set_font_size(self._editor.font().pointSize() - 1)

    def _increase_font_size(self) -> None:
        self._set_font_size(self._editor.font().pointSize() + 1)

    def _set_font_size(self, requested: int) -> None:
        point_size = max(self.MIN_FONT_SIZE, min(requested, self.MAX_FONT_SIZE))
        font = self._editor.font()
        font.setPointSize(point_size)
        self._editor.setFont(font)
        self._editor.setTabStopDistance(
            self._editor.fontMetrics().horizontalAdvance(" ") * 4
        )
        self._editor._update_gutter_width(0)
        self._editor.viewport().update()
        self._editor.line_number_area().update()
        self._sync_font_controls()

    def _sync_font_controls(self) -> None:
        point_size = self._editor.font().pointSize()
        self._font_size_label.setText(f"{point_size} pt")
        self._font_decrease.setEnabled(point_size > self.MIN_FONT_SIZE)
        self._font_increase.setEnabled(point_size < self.MAX_FONT_SIZE)

    def _sync_line_range(self, block_count: int) -> None:
        maximum = max(1, block_count)
        self._line_spin.setRange(1, maximum)
        self._line_spin.setValue(
            min(self._editor.textCursor().blockNumber() + 1, maximum)
        )

    def _sync_position(self) -> None:
        cursor = self._editor.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.positionInBlock() + 1
        self._line_spin.setValue(line)
        self._position_label.setText(f"行 {line}，列 {column}")

    def load_path(self, path: Path) -> None:
        path = Path(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        self._path = path.resolve()
        self.load_text(text, path.suffix)

    def load_text(self, text: str, suffix: str) -> None:
        self._editor.setPlainText(text)
        if self._highlighter is not None:
            self._highlighter.setDocument(None)
        self._highlighter = highlighter_for(suffix, self._editor.document())
        self._editor._update_gutter_width(0)
        self._editor.viewport().update()
        self._editor.line_number_area().update()
        self._sync_line_range(self._editor.blockCount())
        self._sync_position()
