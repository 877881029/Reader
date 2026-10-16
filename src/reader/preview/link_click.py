"""Ctrl+click to open http(s) links in plain-text editors (like VS Code)."""

from __future__ import annotations

import re

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QUrl
from PySide6.QtGui import QColor, QCursor, QDesktopServices, QTextCharFormat, QTextCursor, QTextFormat
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit

# Stop at whitespace, quotes, angle brackets and full-width (CJK) punctuation.
_URL = re.compile(
    r"https?://(?=[^\s/])[^\s<>\"'`，。；：！？、（）【】「」『』《》]+",
    re.IGNORECASE,
)
_TRAILING = ".,;:!?'\""
_PAIRS = {")": "(", "]": "[", "}": "{"}
_LINK_MARK = QTextFormat.Property.UserProperty + 37
LINK_COLOR = "#2563eb"


def _trim(url: str) -> str:
    while url:
        last = url[-1]
        if last in _TRAILING:
            url = url[:-1]
        elif last in _PAIRS and url.count(last) > url.count(_PAIRS[last]):
            url = url[:-1]
        else:
            break
    return url


def url_spans(text: str) -> list[tuple[int, int, str]]:
    spans = []
    for match in _URL.finditer(text):
        url = _trim(match.group(0))
        if "://" in url and len(url) > url.index("://") + 3:
            spans.append((match.start(), match.start() + len(url), url))
    return spans


def url_at(text: str, column: int) -> str | None:
    for start, end, url in url_spans(text):
        if start <= column < end:
            return url
    return None


def open_url(url: str) -> None:
    target = QUrl(url)
    if target.isValid() and target.scheme().lower() in {"http", "https"}:
        QDesktopServices.openUrl(target)


class LinkClicker(QObject):
    """Event filter: Ctrl+hover underlines a URL, Ctrl+click opens it."""

    def __init__(self, editor: QPlainTextEdit) -> None:
        super().__init__(editor)
        self.setObjectName("linkClicker")
        self._editor = editor
        self._active = False
        viewport = editor.viewport()
        viewport.setMouseTracking(True)
        viewport.installEventFilter(self)
        editor.installEventFilter(self)

    @staticmethod
    def hover(editor: QPlainTextEdit, pos: QPoint, *, ctrl: bool) -> str | None:
        clicker = editor.findChild(LinkClicker, "linkClicker")
        return clicker._update(pos, ctrl) if clicker is not None else None

    def _link_under(self, pos: QPoint) -> tuple[int, int, str] | None:
        editor = self._editor
        cursor = editor.cursorForPosition(pos)
        block = cursor.block()
        for start, end, url in url_spans(block.text()):
            first = QTextCursor(block)
            first.setPosition(block.position() + start)
            last = QTextCursor(block)
            last.setPosition(block.position() + end)
            left = editor.cursorRect(first)
            right = editor.cursorRect(last)
            if left.top() <= pos.y() <= left.bottom() and left.left() <= pos.x() <= right.left():
                return block.position() + start, block.position() + end, url
            # Wrapped URLs span several visual lines: fall back to the text column.
            if left.top() != right.top() and start <= cursor.positionInBlock() < end:
                return block.position() + start, block.position() + end, url
        return None

    def _update(self, pos: QPoint | None, ctrl: bool) -> str | None:
        link = self._link_under(pos) if ctrl and pos is not None else None
        editor = self._editor
        selections = [
            item for item in editor.extraSelections() if not item.format.property(_LINK_MARK)
        ]
        if link is None:
            if self._active:
                editor.viewport().unsetCursor()
                editor.setExtraSelections(selections)
                self._active = False
            return None
        start, end, url = link
        underline = QTextEdit.ExtraSelection()
        fmt = QTextCharFormat()
        fmt.setFontUnderline(True)
        fmt.setForeground(QColor(LINK_COLOR))
        fmt.setProperty(_LINK_MARK, True)
        underline.format = fmt
        cursor = QTextCursor(editor.document())
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        underline.cursor = cursor
        editor.setExtraSelections([*selections, underline])
        editor.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        self._active = True
        return url

    def eventFilter(self, watched, event: QEvent) -> bool:  # noqa: N802 - Qt API
        kind = event.type()
        try:
            viewport = self._editor.viewport()
        except RuntimeError:  # editor already destroyed; late teardown events
            return False
        if watched is viewport:
            if kind == QEvent.Type.MouseMove:
                ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
                self._update(event.position().toPoint(), ctrl)
            elif (
                kind == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.LeftButton
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier
            ):
                link = self._link_under(event.position().toPoint())
                if link is not None:
                    open_url(link[2])
                    self._update(None, False)
                    return True
            elif kind == QEvent.Type.Leave:
                self._update(None, False)
        elif watched is self._editor and kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            if event.key() == Qt.Key.Key_Control:
                self._update(viewport.mapFromGlobal(QCursor.pos()), kind == QEvent.Type.KeyPress)
        return super().eventFilter(watched, event)
