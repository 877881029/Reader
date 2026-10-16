from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt, Signal
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from reader.preview.link_click import LinkClicker
from reader.preview.syntax import highlighter_for
from reader.text_io import TextFile, default_text_file, read_text_file, write_text_file
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
    zoom_requested = Signal(int)
    zoom_reset_requested = Signal()
    wrap_toggle_requested = Signal()

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

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt API
        modifiers = event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
        key = event.key()
        if modifiers == Qt.KeyboardModifier.ControlModifier or modifiers == (
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        ):
            if key in (Qt.Key.Key_Equal, Qt.Key.Key_Plus):
                self.zoom_requested.emit(1)
                return
            if key in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
                self.zoom_requested.emit(-1)
                return
            if key == Qt.Key.Key_0 and modifiers == Qt.KeyboardModifier.ControlModifier:
                self.zoom_reset_requested.emit()
                return
        if modifiers == Qt.KeyboardModifier.AltModifier and key == Qt.Key.Key_Z:
            self.wrap_toggle_requested.emit()
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt API
        # Route Ctrl+wheel to the view so the gutter and status bar stay in sync.
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                self.zoom_requested.emit(1 if delta > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)

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


_TYPE_NAMES = {
    ".txt": "Plain text",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".inl": "C++",
    ".ipp": "C++",
    ".hpp": "C++ Header",
    ".hh": "C++ Header",
    ".hxx": "C++ Header",
}


class CodeTextView(QWidget):
    MIN_FONT_SIZE = 8
    MAX_FONT_SIZE = 24
    DEFAULT_FONT_SIZE = 12

    dirty_changed = Signal(bool)
    path_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("codeTextView")
        self._path: Path | None = None
        self._suffix = ""
        self._format: TextFile | None = None
        self._highlighter = None
        self._editor = CodeEditor(self)
        LinkClicker(self._editor)
        self._status_bar = QFrame(self)
        self._status_bar.setObjectName("codeStatusBar")
        status_layout = QHBoxLayout(self._status_bar)
        status_layout.setContentsMargins(14, 0, 14, 0)
        status_layout.setSpacing(0)
        self._position_label = self._status_label("codeStatusPosition", "Ln 1, Col 1")
        self._font_size_label = self._status_label("codeStatusSize", "Size 12 pt")
        self._type_label = self._status_label("codeStatusType", "Type Plain text")
        self._readonly_notice = self._status_label("codeReadOnlyNotice", "只读：无法无损识别编码")
        self._readonly_notice.hide()
        for index, label in enumerate((self._position_label, self._font_size_label, self._type_label)):
            if index:
                status_layout.addWidget(self._status_separator())
            status_layout.addWidget(label)
        status_layout.addStretch(1)
        status_layout.addWidget(self._readonly_notice)
        self._status_bar.setFixedHeight(26)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._editor)
        layout.addWidget(self._status_bar)
        self.setStyleSheet(
            f"""
            #codeTextView {{ background: {PAPER}; }}
            #codeStatusBar {{
                background: {CHROME};
                border-top: 1px solid {LINE};
            }}
            #codeStatusBar QLabel {{
                color: {MUTED};
                font-size: 12px;
                padding: 0 12px;
            }}
            #codeStatusBar QFrame#codeStatusSeparator {{
                background: {LINE};
                border: none;
            }}
            """
        )
        self._editor.blockCountChanged.connect(lambda _count: self._sync_position())
        self._editor.cursorPositionChanged.connect(self._sync_position)
        self._editor.document().modificationChanged.connect(self.dirty_changed)
        self._editor.zoom_requested.connect(lambda steps: self._set_font_size(self.font_size() + steps))
        self._editor.zoom_reset_requested.connect(lambda: self._set_font_size(self.DEFAULT_FONT_SIZE))
        self._editor.wrap_toggle_requested.connect(lambda: self.set_wrap(not self.wrap_enabled()))
        self._sync_font_controls()

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def suffix(self) -> str:
        return self._suffix

    @property
    def dirty(self) -> bool:
        return self._editor.document().isModified()

    def text(self) -> str:
        return self._editor.toPlainText()

    def is_editable(self) -> bool:
        return not self._editor.isReadOnly()

    def display_title(self) -> str:
        name = self._path.name if self._path is not None else f"未命名{self._suffix or '.txt'}"
        return f"*{name}" if self.dirty else name

    def save(self) -> bool:
        if self._path is None or self._format is None or not self._format.lossless:
            return False
        write_text_file(self._path, self.text(), self._format)
        self._editor.document().setModified(False)
        return True

    def save_as(self, path: Path) -> None:
        target = Path(path)
        if target.suffix == "":
            target = target.with_suffix(self._suffix or ".txt")
        fmt = self._format if self._format is not None and self._format.lossless else default_text_file()
        write_text_file(target, self.text(), fmt)
        self._format = fmt
        self._path = target.resolve()
        if target.suffix.lower() != self._suffix.lower():
            self._suffix = target.suffix
            self._apply_highlighter()
        self._editor.document().setModified(False)
        self.path_changed.emit(self._path)

    def draft_state(self) -> dict:
        """Everything needed to restore this unsaved edit after a restart."""
        fmt = self._format or default_text_file()
        suffix = self._suffix or ".txt"
        return {
            "kind": "text",
            "path": self._path,
            "suffix": suffix,
            "title": self._path.name if self._path is not None else f"未命名{suffix}",
            "text": self.text(),
            "encoding": fmt.encoding,
            "bom": fmt.bom,
            "newline": fmt.newline,
            "lossless": fmt.lossless,
        }

    def restore_draft(
        self, *, kind: str, path, suffix: str, title: str, text: str,
        encoding: str, bom: bool, newline: str, lossless: bool,
    ) -> None:
        self._path = Path(path).resolve() if path is not None else None
        self._format = TextFile(text="", encoding=encoding, bom=bom, newline=newline, lossless=lossless)
        self._show_text(text, suffix or ".txt", editable=lossless)
        self._editor.document().setModified(True)

    def load_untitled(self, suffix: str = ".txt") -> None:
        self._path = None
        self._format = default_text_file()
        self._show_text("", suffix, editable=True)

    def _set_editable(self, editable: bool) -> None:
        self._editor.setReadOnly(not editable)
        flags = (
            Qt.TextInteractionFlag.TextEditorInteraction
            if editable
            else Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self._editor.setTextInteractionFlags(flags)

    def _apply_highlighter(self) -> None:
        if self._highlighter is not None:
            self._highlighter.setDocument(None)
        self._highlighter = highlighter_for(self._suffix, self._editor.document())

    def editor(self) -> CodeEditor:
        return self._editor

    def line_number_area(self) -> QWidget:
        return self._editor.line_number_area()

    def line_number_area_width(self) -> int:
        return self._editor.line_number_area_width()

    def highlighter(self):
        return self._highlighter

    def _status_label(self, name: str, text: str) -> QLabel:
        label = QLabel(text, self._status_bar)
        label.setObjectName(name)
        label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        return label

    def _status_separator(self) -> QFrame:
        separator = QFrame(self._status_bar)
        separator.setObjectName("codeStatusSeparator")
        separator.setFixedSize(1, 14)
        return separator

    def jump_to_line(self, line: int) -> None:
        line = max(1, min(int(line), self._editor.blockCount()))
        block = self._editor.document().findBlockByNumber(line - 1)
        self._editor.setTextCursor(QTextCursor(block))
        self._editor.centerCursor()

    def wrap_enabled(self) -> bool:
        return self._editor.lineWrapMode() != QPlainTextEdit.LineWrapMode.NoWrap

    def set_wrap(self, enabled: bool) -> None:
        mode = (
            QPlainTextEdit.LineWrapMode.WidgetWidth
            if enabled
            else QPlainTextEdit.LineWrapMode.NoWrap
        )
        self._editor.setLineWrapMode(mode)

    def font_size(self) -> int:
        return self._editor.font().pointSize()

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
        self._font_size_label.setText(f"Size {self.font_size()} pt")

    def _sync_type(self) -> None:
        name = _TYPE_NAMES.get(self._suffix.lower()) or (self._suffix.lstrip(".").upper() or "Plain text")
        self._type_label.setText(f"Type {name}")

    def _sync_position(self) -> None:
        cursor = self._editor.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.positionInBlock() + 1
        self._position_label.setText(f"Ln {line}, Col {column}")

    def load_path(self, path: Path) -> None:
        path = Path(path)
        loaded = read_text_file(path)
        self._path = path.resolve()
        self._format = loaded
        self._show_text(loaded.text, path.suffix, editable=loaded.lossless)

    def load_text(self, text: str, suffix: str) -> None:
        self._path = None
        self._format = None
        self._show_text(text, suffix, editable=False)

    def _show_text(self, text: str, suffix: str, *, editable: bool) -> None:
        self._suffix = suffix
        self._editor.setPlainText(text)
        self._apply_highlighter()
        self._set_editable(editable)
        self._readonly_notice.setHidden(
            self._format is None or self._format.lossless
        )
        self._editor.document().clearUndoRedoStacks()
        self._editor.document().setModified(False)
        self._editor._update_gutter_width(0)
        self._editor.viewport().update()
        self._editor.line_number_area().update()
        self._sync_type()
        self._sync_position()
