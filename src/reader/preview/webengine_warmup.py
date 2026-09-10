from __future__ import annotations

import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication

_WARMED = False
_VIEW = None
WARMUP_DELAY_MS = 400
_SKIP_VALUES = {"1", "true", "yes", "on"}


def _skip_warmup() -> bool:
    value = os.environ.get("READER_SKIP_WEBENGINE_WARMUP", "")
    return value.strip().lower() in _SKIP_VALUES


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
