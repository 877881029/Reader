from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QTextCursor, QTextDocument
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QWidget


@dataclass(frozen=True)
class FindOutcome:
    found: bool
    pending: bool = False


def resolve_find_target(widget: QWidget | None) -> QWidget | None:
    if widget is None:
        return None
    from PySide6.QtWebEngineWidgets import QWebEngineView

    if isinstance(widget, (QPlainTextEdit, QWebEngineView, QLabel)):
        return widget
    editor = getattr(widget, "editor", None)
    if callable(editor):
        inner = editor()
        if isinstance(inner, QPlainTextEdit):
            return inner
    plain = widget.findChild(QPlainTextEdit)
    if plain is not None:
        return plain
    web = widget.findChild(QWebEngineView)
    if web is not None:
        return web
    return widget


def find_in_widget(
    widget: QWidget | None,
    query: str,
    *,
    forward: bool = True,
    case_sensitive: bool = False,
    wrap: bool = True,
    on_result=None,
) -> FindOutcome:
    target = resolve_find_target(widget)
    if target is None or not query:
        outcome = FindOutcome(found=False)
        if on_result is not None:
            on_result(False)
        return outcome

    from PySide6.QtWebEngineCore import QWebEnginePage
    from PySide6.QtWebEngineWidgets import QWebEngineView

    if isinstance(target, QPlainTextEdit):
        found = _find_plain(
            target,
            query,
            forward=forward,
            case_sensitive=case_sensitive,
            wrap=wrap,
        )
        if on_result is not None:
            on_result(found)
        return FindOutcome(found=found)

    if isinstance(target, QWebEngineView):
        flags = QWebEnginePage.FindFlag(0)
        if not forward:
            flags |= QWebEnginePage.FindFlag.FindBackward
        if case_sensitive:
            flags |= QWebEnginePage.FindFlag.FindCaseSensitively
        page = target.page()

        def _finished(result) -> None:
            try:
                page.findTextFinished.disconnect(_finished)
            except (RuntimeError, TypeError):
                pass
            found = int(result.numberOfMatches()) > 0
            if on_result is not None:
                on_result(found)

        page.findTextFinished.connect(_finished)
        page.findText(query, flags)
        return FindOutcome(found=False, pending=True)

    text = target.text() if callable(getattr(target, "text", None)) else ""
    if case_sensitive:
        found = query in text
    else:
        found = query.lower() in text.lower()
    if on_result is not None:
        on_result(found)
    return FindOutcome(found=found)


def clear_find_highlights(widget: QWidget | None) -> None:
    target = resolve_find_target(widget)
    if target is None:
        return
    from PySide6.QtWebEngineWidgets import QWebEngineView

    if isinstance(target, QWebEngineView):
        target.page().findText("")


def _find_plain(
    editor: QPlainTextEdit,
    query: str,
    *,
    forward: bool,
    case_sensitive: bool,
    wrap: bool,
) -> bool:
    flags = QTextDocument.FindFlag(0)
    if not forward:
        flags |= QTextDocument.FindFlag.FindBackward
    if case_sensitive:
        flags |= QTextDocument.FindFlag.FindCaseSensitively
    if editor.find(query, flags):
        return True
    if not wrap:
        return False
    cursor = editor.textCursor()
    cursor.clearSelection()
    if forward:
        cursor.movePosition(QTextCursor.MoveOperation.Start)
    else:
        cursor.movePosition(QTextCursor.MoveOperation.End)
    editor.setTextCursor(cursor)
    return editor.find(query, flags)


def _find_flags(case_sensitive: bool) -> QTextDocument.FindFlag:
    flags = QTextDocument.FindFlag(0)
    if case_sensitive:
        flags |= QTextDocument.FindFlag.FindCaseSensitively
    return flags


def _selection_matches(editor: QPlainTextEdit, query: str, case_sensitive: bool) -> bool:
    selected = editor.textCursor().selectedText()
    if case_sensitive:
        return selected == query
    return selected.casefold() == query.casefold()


def replace_current(
    editor: QPlainTextEdit,
    query: str,
    replacement: str,
    *,
    case_sensitive: bool,
) -> bool:
    """Replace the selected match (if any), then select the next match.

    Returns whether a following match was found.
    """
    if not query or editor.isReadOnly():
        return False
    if _selection_matches(editor, query, case_sensitive):
        editor.textCursor().insertText(replacement)
    return _find_plain(
        editor,
        query,
        forward=True,
        case_sensitive=case_sensitive,
        wrap=True,
    )


def replace_all(
    editor: QPlainTextEdit,
    query: str,
    replacement: str,
    *,
    case_sensitive: bool,
) -> int:
    """Replace every match as a single undo step and return the count."""
    if not query or editor.isReadOnly():
        return 0
    document = editor.document()
    flags = _find_flags(case_sensitive)
    spans: list[tuple[int, int]] = []
    found = document.find(query, 0, flags)
    while not found.isNull():
        spans.append((found.selectionStart(), found.selectionEnd()))
        found = document.find(query, found.selectionEnd(), flags)
    if not spans:
        return 0
    cursor = QTextCursor(document)
    cursor.beginEditBlock()
    for start, end in reversed(spans):
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(replacement)
    cursor.endEditBlock()
    return len(spans)
