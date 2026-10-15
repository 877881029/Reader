from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from reader.theme import PAPER

_WARMED = False
_VIEW = None
WARMUP_DELAY_MS = 50
# Opening only natively drawn files: let them paint before Chromium starts.
DEFERRED_WARMUP_MS = 2000
_SKIP_VALUES = {"1", "true", "yes", "on"}


def _skip_warmup() -> bool:
    value = os.environ.get("READER_SKIP_WEBENGINE_WARMUP", "")
    return value.strip().lower() in _SKIP_VALUES


def needs_webengine(paths: Iterable[str]) -> bool:
    """True when any path is shown through Chromium (not a native Qt viewer)."""
    from reader.formats.binary import BINARY_SUFFIXES
    from reader.formats.code import CODE_SUFFIXES
    from reader.formats.image import IMAGE_SUFFIXES

    native = CODE_SUFFIXES | IMAGE_SUFFIXES | BINARY_SUFFIXES | {".svg"}
    return any(Path(path).suffix.lower() not in native for path in paths)


def kept_view():
    return _VIEW


def warmup_webengine(app: QApplication | None = None) -> bool:
    """Start Chromium once and keep a hidden view so the first document is not cold."""
    global _WARMED, _VIEW
    if _WARMED:
        return False
    qapp = app or QApplication.instance()
    if qapp is None:
        return False
    try:
        from PySide6.QtWebEngineWidgets import QWebEngineView

        view = QWebEngineView()
        view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        view.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        view.resize(8, 8)
        view.hide()
        view.page().setBackgroundColor(QColor(PAPER))
        view.setHtml("<!doctype html><title>warmup</title>")
    except Exception:
        return False
    _VIEW = view
    _WARMED = True
    return True


def schedule_webengine_warmup(
    app: QApplication | None = None,
    *,
    delay_ms: int | None = None,
) -> None:
    if _skip_warmup():
        return
    qapp = app or QApplication.instance()
    if qapp is None:
        return
    wait = WARMUP_DELAY_MS if delay_ms is None else delay_ms
    QTimer.singleShot(wait, lambda: warmup_webengine(qapp))


def reset_warmup_for_tests() -> None:
    global _WARMED, _VIEW
    view = _VIEW
    _VIEW = None
    _WARMED = False
    if view is not None:
        view.deleteLater()
