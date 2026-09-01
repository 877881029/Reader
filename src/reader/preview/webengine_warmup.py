from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

_WARMED = False


def warmup_webengine(app: QApplication | None = None) -> bool:
    """Idempotent Chromium warm-up so the first visual open is closer to the second."""
    global _WARMED
    if _WARMED:
        return False
    qapp = app or QApplication.instance()
    if qapp is None:
        return False
    try:
        from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile

        profile = QWebEngineProfile(qapp)
        page = QWebEnginePage(profile, profile)
        page.setHtml("<!doctype html><title>warmup</title>")
        qapp.processEvents()
        page.deleteLater()
        profile.deleteLater()
    except Exception:
        return False
    _WARMED = True
    return True


def schedule_webengine_warmup(app: QApplication | None = None, *, delay_ms: int = 0) -> None:
    qapp = app or QApplication.instance()
    if qapp is None:
        return
    QTimer.singleShot(delay_ms, lambda: warmup_webengine(qapp))


def reset_warmup_for_tests() -> None:
    global _WARMED
    _WARMED = False
