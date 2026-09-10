from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QResizeEvent, QTextCharFormat, QTextFormat
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPlainTextEdit, QTextEdit, QWidget

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
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("codeTextView")
        self._path: Path | None = None
        self._highlighter = None
        self._editor = CodeEditor(self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._editor)
        self.setStyleSheet(f"#codeTextView {{ background: {PAPER}; }}")

    def editor(self) -> CodeEditor:
        return self._editor

    def line_number_area(self) -> QWidget:
        return self._editor.line_number_area()

    def line_number_area_width(self) -> int:
        return self._editor.line_number_area_width()

    def highlighter(self):
        return self._highlighter

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
