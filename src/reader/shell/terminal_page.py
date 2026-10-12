"""Terminal tab: ConPTY shell rendered by an offline xterm.js page."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineUrlRequestInterceptor,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from reader.resources import resource_path
from reader.terminal.pty_session import SHELL_PROFILES, PtySession

EXIT_HINT = "[进程已退出，按 Enter 重新启动]"
_BACKGROUND = "#fbf9f5"
_ALLOWED_SCHEMES = frozenset({"qrc", "data", "blob"})


def _canonical(path: str | Path) -> str:
    return os.path.normcase(os.path.realpath(os.fspath(path)))


class _BundleOnlyInterceptor(QWebEngineUrlRequestInterceptor):
    """Only the terminal bundle and Qt resources may load; nothing else."""

    def __init__(self, bundle_root: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._root = _canonical(bundle_root)

    def allows(self, url: QUrl) -> bool:
        scheme = url.scheme().lower()
        if scheme in _ALLOWED_SCHEMES:
            return True
        if scheme != "file" or not url.toLocalFile():
            return False
        candidate = _canonical(url.toLocalFile())
        try:
            return os.path.commonpath((candidate, self._root)) == self._root
        except ValueError:
            return False

    def interceptRequest(self, info) -> None:  # noqa: N802 - Qt virtual method
        if not self.allows(info.requestUrl()):
            info.block(True)


class TerminalBridge(QObject):
    """QWebChannel object shared with the xterm.js page."""

    output = Signal(str)

    def __init__(self, owner: TerminalPage) -> None:
        super().__init__(owner)
        self._owner = owner

    @Slot(int, int)
    def ready(self, cols: int, rows: int) -> None:
        self._owner._on_ready(cols, rows)

    @Slot(str)
    def input(self, data: str) -> None:
        self._owner._on_input(data)

    @Slot(int, int)
    def resize(self, cols: int, rows: int) -> None:
        self._owner._on_resize(cols, rows)

    @Slot(str)
    def copyText(self, text: str) -> None:  # noqa: N802 - JS-facing name
        QApplication.clipboard().setText(text)


class TerminalPage(QWidget):
    def __init__(self, profile: str, cwd: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("terminalPage")
        self._profile_key = profile
        self._profile = SHELL_PROFILES[profile]
        self._cwd = Path(cwd)
        self._session: PtySession | None = None
        self._size = (80, 24)
        self._exited = False
        self._shutdown = False

        app = QApplication.instance()
        if app is None:
            raise RuntimeError("TerminalPage requires QApplication")
        index = resource_path("assets", "terminal-viewer", "index.html").resolve()
        self._bundle_root = index.parent
        # No storage name => off-the-record; isolated from every other view.
        self._web_profile: QWebEngineProfile | None = QWebEngineProfile(app)
        self._interceptor = _BundleOnlyInterceptor(self._bundle_root, self._web_profile)
        self._web_profile.setUrlRequestInterceptor(self._interceptor)
        self._web_page: QWebEnginePage | None = QWebEnginePage(self._web_profile, self._web_profile)
        self._web_page.setBackgroundColor(QColor(_BACKGROUND))
        self._channel = QWebChannel(self._web_page)
        self._bridge = TerminalBridge(self)
        self._channel.registerObject("bridge", self._bridge)
        self._web_page.setWebChannel(self._channel)

        self._view = QWebEngineView(self)
        self._view.setObjectName("terminalView")
        self._view.setPage(self._web_page)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)
        self._view.load(QUrl.fromLocalFile(str(index)))

    # -- public API -----------------------------------------------------------------

    def title(self) -> str:
        return self._profile.title

    def profile_key(self) -> str:
        return self._profile_key

    def cwd(self) -> Path:
        return self._cwd

    def view(self) -> QWebEngineView:
        return self._view

    def bridge(self) -> TerminalBridge:
        return self._bridge

    def bundle_root(self) -> Path:
        return self._bundle_root

    def allows_url(self, url: QUrl) -> bool:
        return self._interceptor.allows(url)

    def session(self) -> PtySession | None:
        return self._session

    def is_ready(self) -> bool:
        return self._session is not None and self._session.is_running()

    def focus_terminal(self) -> None:
        self._view.setFocus()
        if self._web_page is not None:
            self._web_page.runJavaScript(
                "window.readerTerminal && window.readerTerminal.terminal.focus()"
            )

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self._stop_session()
        self._view.stop()
        self._view.setPage(QWebEnginePage(self._view))
        for obj in (self._web_page, self._web_profile):
            if obj is not None:
                obj.setParent(None)
                obj.deleteLater()
        self._web_page = None
        self._web_profile = None

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        self.shutdown()
        super().closeEvent(event)

    # -- bridge callbacks -----------------------------------------------------------

    def _on_ready(self, cols: int, rows: int) -> None:
        self._size = (cols, rows)
        if self._session is None and not self._exited:
            self._start_session()

    def _on_input(self, data: str) -> None:
        if self._session is not None:
            self._session.write(data)
        elif self._exited and "\r" in data:
            self._exited = False
            self._start_session()

    def _on_resize(self, cols: int, rows: int) -> None:
        self._size = (cols, rows)
        if self._session is not None:
            self._session.resize(cols, rows)

    # -- session --------------------------------------------------------------------

    def _start_session(self) -> None:
        if self._shutdown:
            return
        session = PtySession(self._profile_key, self._cwd, self)
        session.output.connect(self._bridge.output)
        session.exited.connect(self._on_exited)
        self._session = session
        session.start(*self._size)

    def _stop_session(self) -> None:
        session, self._session = self._session, None
        if session is not None:
            session.shutdown()
            session.deleteLater()

    def _on_exited(self, _code: int) -> None:
        session, self._session = self._session, None
        if session is not None:
            session.deleteLater()
        self._exited = True
        self._bridge.output.emit(f"\r\n\x1b[90m{EXIT_HINT}\x1b[0m\r\n")