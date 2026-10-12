"""Lightweight in-tab web browser (``+`` → Browser)."""

from __future__ import annotations

import re
from urllib.parse import quote

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLineEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from reader.theme import CARD, HOVER, INK, LINE, MUTED, PAPER

SEARCH_URL = "https://www.bing.com/search?q="
_DIRECT_SCHEMES = {"http", "https", "file"}
_LOCALHOST = re.compile(r"^localhost(:\d{1,5})?(/.*)?$", re.IGNORECASE)
_HOSTLIKE = re.compile(r"^[^\s/:]+\.[^\s/:]+(:\d{1,5})?(/\S*)?$")


def normalize_address(text: str) -> QUrl | None:
    """Turn address-bar input into a safe URL; anything unusual becomes a search."""
    stripped = text.strip()
    if not stripped:
        return None
    scheme = stripped.split(":", 1)[0].lower() if ":" in stripped else ""
    if scheme in _DIRECT_SCHEMES and "://" in stripped:
        url = QUrl(stripped, QUrl.ParsingMode.StrictMode)
        if url.isValid():
            return url
    if " " not in stripped:
        if _LOCALHOST.match(stripped):
            return QUrl(f"http://{stripped}")
        if _HOSTLIKE.match(stripped):
            return QUrl(f"https://{stripped}")
    return QUrl(SEARCH_URL + quote(stripped, safe="()"), QUrl.ParsingMode.StrictMode)


class BrowserPage(QWidget):
    """Address bar + navigation over an isolated, off-the-record web view."""

    title_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("browserPage")
        self._shutdown = False
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("BrowserPage requires QApplication")

        toolbar = QWidget(self)
        toolbar.setObjectName("browserToolbar")
        toolbar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        toolbar.setFixedHeight(42)
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(10, 6, 10, 6)
        row.setSpacing(4)
        self._back = self._tool_button(toolbar, "browserBack", "←", "后退")
        self._forward = self._tool_button(toolbar, "browserForward", "→", "前进")
        self._reload = self._tool_button(toolbar, "browserReload", "⟳", "刷新")
        self._address = QLineEdit(toolbar)
        self._address.setObjectName("browserAddress")
        self._address.setPlaceholderText("输入网址或搜索")
        self._address.setClearButtonEnabled(True)
        for widget in (self._back, self._forward, self._reload):
            row.addWidget(widget)
        row.addWidget(self._address, 1)

        # No storage name => off-the-record: no cookies/cache written to disk,
        # and nothing shared with the offline Markdown/PPTX viewer profiles.
        self._profile: QWebEngineProfile | None = QWebEngineProfile(app)
        self._page: QWebEnginePage | None = QWebEnginePage(self._profile, self._profile)
        self._page.setBackgroundColor(QColor(PAPER))
        self._view = QWebEngineView(self)
        self._view.setObjectName("browserView")
        self._view.setPage(self._page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(toolbar)
        layout.addWidget(self._view, 1)

        self.setStyleSheet(
            f"""
            QWidget#browserToolbar {{
                background: {PAPER};
                border-bottom: 1px solid {LINE};
            }}
            QToolButton#browserBack, QToolButton#browserForward, QToolButton#browserReload {{
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px 8px;
                color: {INK};
                font-size: 14px;
            }}
            QToolButton#browserBack:hover, QToolButton#browserForward:hover,
            QToolButton#browserReload:hover {{
                background: {HOVER};
            }}
            QToolButton:disabled {{ color: {MUTED}; }}
            QLineEdit#browserAddress {{
                background: {CARD};
                color: {INK};
                border: 1px solid {LINE};
                border-radius: 6px;
                padding: 4px 10px;
            }}
            """
        )

        self._back.clicked.connect(self._view.back)
        self._forward.clicked.connect(self._view.forward)
        self._reload.clicked.connect(self._view.reload)
        self._address.returnPressed.connect(lambda: self.load_address(self._address.text()))
        self._view.urlChanged.connect(self._on_url_changed)
        self._view.titleChanged.connect(self._on_title_changed)
        self._update_history_buttons()
        self._view.setUrl(QUrl("about:blank"))

    @staticmethod
    def _tool_button(parent: QWidget, name: str, text: str, tip: str) -> QToolButton:
        button = QToolButton(parent)
        button.setObjectName(name)
        button.setText(text)
        button.setToolTip(tip)
        button.setAutoRaise(True)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    def view(self) -> QWebEngineView:
        return self._view

    def profile(self) -> QWebEngineProfile | None:
        return self._profile

    def address_edit(self) -> QLineEdit:
        return self._address

    def focus_address(self) -> None:
        self._address.setFocus(Qt.FocusReason.OtherFocusReason)
        self._address.selectAll()

    def load_address(self, text: str) -> bool:
        url = normalize_address(text)
        if url is None or self._shutdown:
            return False
        self._view.setUrl(url)
        self._view.setFocus(Qt.FocusReason.OtherFocusReason)
        return True

    def _on_url_changed(self, url: QUrl) -> None:
        shown = "" if url.toString() == "about:blank" else url.toString()
        self._address.setText(shown)
        self._update_history_buttons()

    def _on_title_changed(self, title: str) -> None:
        url = self._view.url().toString()
        if title and title != url and title != "about:blank":
            self.title_changed.emit(title)

    def _update_history_buttons(self) -> None:
        history = self._view.history()
        self._back.setEnabled(history.canGoBack())
        self._forward.setEnabled(history.canGoForward())

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        try:
            self._view.urlChanged.disconnect(self._on_url_changed)
            self._view.titleChanged.disconnect(self._on_title_changed)
        except (RuntimeError, TypeError):
            pass
        self._view.stop()
        self._view.setPage(QWebEnginePage(self._view))
        for obj in (self._page, self._profile):
            if obj is not None:
                obj.setParent(None)
                obj.deleteLater()
        self._page = None
        self._profile = None

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        self.shutdown()
        super().closeEvent(event)
