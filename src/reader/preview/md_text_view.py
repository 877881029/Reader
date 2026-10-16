from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QFocusEvent, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QFrame, QPlainTextEdit, QVBoxLayout, QWidget

from reader.preview.link_click import LinkClicker
from reader.text_io import TextFile, read_text_file, write_text_file
from reader.theme import INK, PAPER

_UNTITLED_MARKDOWN = TextFile(text="", encoding="utf-8", bom=False, newline="\n", lossless=True)


class MarkdownTextView(QWidget):
    """Fast plain-text Markdown view: read-only until interaction, then editable."""

    dirty_changed = Signal(bool)
    path_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("markdownTextView")
        self._path: Path | None = None
        self._dirty = False
        self._allow_edit = False
        self._loading = False
        self._format: TextFile = _UNTITLED_MARKDOWN

        self._editor = QPlainTextEdit(self)
        self._editor.setObjectName("markdownTextEditor")
        self._editor.setFrameShape(QFrame.Shape.NoFrame)
        self._editor.setStyleSheet(
            f"QPlainTextEdit#markdownTextEditor {{ background: {PAPER}; border: none; color: {INK}; }}"
        )
        self._editor.document().setDocumentMargin(8)
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._editor.viewport().installEventFilter(self)
        self._editor.installEventFilter(self)
        # Installed last so Ctrl+click on a link is handled before the edit-mode switch.
        LinkClicker(self._editor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._editor)
        self._editor.textChanged.connect(self._on_text_changed)

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def dirty(self) -> bool:
        return self._dirty

    def text(self) -> str:
        return self._editor.toPlainText()

    def is_editable(self) -> bool:
        return not self._editor.isReadOnly()

    def load_path(self, path: Path, *, editable: bool = False) -> None:
        loaded = read_text_file(path)
        self._path = path.resolve()
        self._format = loaded
        self._replace_text(loaded.text)
        self._set_editable(editable)
        self.path_changed.emit(self._path)

    def load_untitled(self, *, title_hint: str = "未命名.md") -> None:
        self._path = None
        self._format = _UNTITLED_MARKDOWN
        self._replace_text("")
        self._set_editable(True)
        self.setProperty("readerUntitledTitle", title_hint)
        self.path_changed.emit(None)

    def enable_editing(self) -> None:
        self._set_editable(True)

    def save(self) -> bool:
        if self._path is None or not self._format.lossless:
            return False
        write_text_file(self._path, self.text(), self._format)
        self._mark_clean()
        return True

    def save_as(self, path: Path) -> None:
        path = path.resolve()
        if path.suffix.lower() == "":
            path = path.with_suffix(".md")
        fmt = self._format if self._format.lossless else _UNTITLED_MARKDOWN
        write_text_file(path, self.text(), fmt)
        self._format = fmt
        self._path = path
        self._mark_clean()
        self.path_changed.emit(self._path)

    def display_title(self) -> str:
        if self._path is not None:
            name = self._path.name
        else:
            name = str(self.property("readerUntitledTitle") or "未命名.md")
        return f"*{name}" if self._dirty else name

    def _replace_text(self, text: str) -> None:
        self._loading = True
        self._editor.setPlainText(text)
        self._loading = False
        self._editor.document().clearUndoRedoStacks()
        self._mark_clean()

    def _mark_clean(self) -> None:
        self._editor.document().setModified(False)
        self._set_dirty(False)

    def _set_editable(self, editable: bool) -> None:
        editable = editable and self._format.lossless
        self._allow_edit = editable
        self._editor.setReadOnly(not editable)
        if editable:
            self._editor.setFocus(Qt.FocusReason.MouseFocusReason)

    def _set_dirty(self, dirty: bool) -> None:
        if self._dirty == dirty:
            return
        self._dirty = dirty
        self.dirty_changed.emit(dirty)

    def _on_text_changed(self) -> None:
        if self._loading or self._editor.isReadOnly():
            return
        document = self._editor.document()
        # Undo back to the saved state is the only change that leaves the view clean.
        self._set_dirty(document.isModified() or not document.isRedoAvailable())

    def eventFilter(self, watched, event: QEvent) -> bool:  # noqa: N802
        if watched in {self._editor, self._editor.viewport()}:
            if event.type() == QEvent.Type.MouseButtonPress and not self._allow_edit:
                self.enable_editing()
            elif (
                event.type() == QEvent.Type.KeyPress
                and not self._allow_edit
                and isinstance(event, QKeyEvent)
                and event.text()
            ):
                self.enable_editing()
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._allow_edit:
            self.enable_editing()
        super().mousePressEvent(event)
