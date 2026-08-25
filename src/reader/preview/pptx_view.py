from __future__ import annotations

import threading
from pathlib import Path

import PySide6.QtWebChannel  # noqa: F401 - registers :/qtwebchannel/qwebchannel.js
from PySide6.QtCore import (
    QFile,
    QIODevice,
    QObject,
    Property,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineSettings,
    QWebEngineUrlRequestInterceptor,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget

from reader.preview.result import PreviewResult
from reader.resources import resource_path

_ALLOWED_SCHEMES = frozenset({"file", "qrc", "data", "blob"})
_DISPOSE_SCRIPT = (
    "if (typeof window.readerPptxDispose === 'function') "
    "{ window.readerPptxDispose(); }"
)


class OfflineRequestInterceptor(QWebEngineUrlRequestInterceptor):
    """Block non-local requests without emitting signals from Chromium threads."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lock = threading.Lock()
        self._blocked: list[str] = []

    def interceptRequest(self, info) -> None:  # noqa: N802 - Qt virtual method
        url = info.requestUrl()
        if url.scheme().lower() in _ALLOWED_SCHEMES:
            return
        with self._lock:
            self._blocked.append(url.toString())
        info.block(True)

    def blocked_urls(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._blocked)


class PptxBridge(QObject):
    ready = Signal(int)
    failed = Signal(str)
    changed = Signal(int)

    def __init__(
        self,
        source: Path,
        test_fail_slide: int | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._source_url = QUrl.fromLocalFile(str(source.resolve())).toString(
            QUrl.ComponentFormattingOption.FullyEncoded
        )
        self._test_fail_slide = test_fail_slide

    @Property(str, constant=True)
    def sourceUrl(self) -> str:  # noqa: N802 - WebChannel contract
        return self._source_url

    @Property(int, constant=True)
    def testFailSlide(self) -> int:  # noqa: N802 - WebChannel contract
        if self._test_fail_slide is None:
            return -1
        return self._test_fail_slide

    @Slot(int)
    def viewerReady(self, count: int) -> None:  # noqa: N802 - WebChannel contract
        self.ready.emit(count)

    @Slot(str)
    def viewerError(self, message: str) -> None:  # noqa: N802
        self.failed.emit(message)

    @Slot(int)
    def slideChanged(self, index: int) -> None:  # noqa: N802
        self.changed.emit(index)


class PptxVisualView(QWebEngineView):
    ready = Signal(int)
    slide_changed = Signal(int)
    render_failed = Signal(str)

    def __init__(
        self,
        result: PreviewResult,
        source: Path,
        parent: QWidget | None = None,
        test_fail_slide: int | None = None,
    ) -> None:
        super().__init__(parent)
        self._result = result
        self._source = source.resolve()
        self.started = False
        self.is_fallback = False
        self._shutdown = False
        self._startup_complete = False
        self._load_connected = False
        self._bootstrap_error: str | None = None

        self.viewer_url = QUrl.fromLocalFile(
            str(resource_path("assets", "pptx-viewer", "index.html").resolve())
        )
        self.startup_timer = QTimer(self)
        self.startup_timer.setSingleShot(True)
        self.startup_timer.setInterval(15_000)
        self.startup_timer.timeout.connect(self._startup_timeout)

        self.profile: QWebEngineProfile | None = QWebEngineProfile(self)
        self.interceptor: OfflineRequestInterceptor | None = OfflineRequestInterceptor(
            self.profile
        )
        self.profile.setUrlRequestInterceptor(self.interceptor)

        page = QWebEnginePage(self.profile, self.profile)
        settings = page.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False
        )

        self.channel: QWebChannel | None = QWebChannel(self)
        self.bridge: PptxBridge | None = PptxBridge(
            self._source, test_fail_slide, self.channel
        )
        self.channel.registerObject("bridge", self.bridge)
        page.setWebChannel(self.channel)
        self.setPage(page)

        self.loadFinished.connect(self._load_finished)
        self._load_connected = True
        self.bridge.ready.connect(self._viewer_ready)
        self.bridge.failed.connect(self._bridge_failed)
        self.bridge.changed.connect(self.slide_changed)

        script_source = self._read_webchannel_script()
        if script_source:
            script = QWebEngineScript()
            script.setName("reader-qwebchannel")
            script.setInjectionPoint(
                QWebEngineScript.InjectionPoint.DocumentCreation
            )
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            script.setRunsOnSubFrames(False)
            script.setSourceCode(script_source)
            page.scripts().insert(script)
        else:
            self._bootstrap_error = "Qt WebChannel script unavailable"
            QTimer.singleShot(
                0,
                lambda: self._show_fallback(self._bootstrap_error)
                if self._bootstrap_error is not None
                else None,
            )

    @staticmethod
    def _read_webchannel_script() -> str:
        source = QFile(":/qtwebchannel/qwebchannel.js")
        if not source.open(QIODevice.OpenModeFlag.ReadOnly):
            return ""
        try:
            payload = bytes(source.readAll())
        finally:
            source.close()
        if not payload:
            return ""
        return payload.decode("utf-8")

    def start(self) -> None:
        if (
            self.started
            or self.is_fallback
            or self._shutdown
            or self._bootstrap_error is not None
        ):
            return
        self.started = True
        self.startup_timer.start()
        self.load(self.viewer_url)

    @Slot(bool)
    def _load_finished(self, succeeded: bool) -> None:
        if not succeeded:
            self._show_fallback("viewer bundle failed to load")

    @Slot()
    def _startup_timeout(self) -> None:
        if self._startup_complete:
            return
        self._show_fallback("viewer startup timed out")

    @Slot(int)
    def _viewer_ready(self, count: int) -> None:
        if self._shutdown or self.is_fallback:
            return
        self._startup_complete = True
        self.startup_timer.stop()
        self.ready.emit(count)

    @Slot(str)
    def _bridge_failed(self, message: str) -> None:
        self._show_fallback(message or "viewer render failed")

    def _disconnect_load_finished(self) -> None:
        if not self._load_connected:
            return
        try:
            self.loadFinished.disconnect(self._load_finished)
        except (RuntimeError, TypeError):
            pass
        self._load_connected = False

    def _show_fallback(self, reason: str | None) -> None:
        if self.is_fallback or self._shutdown:
            return
        self.is_fallback = True
        self.startup_timer.stop()
        self.stop()
        self._disconnect_load_finished()
        fallback = self._result.fallback_html or (
            "<!doctype html><meta charset='utf-8'>"
            "<p>演示文稿无法进行视觉渲染。</p>"
        )
        self.setHtml(
            fallback,
            QUrl.fromLocalFile(str(self._source.parent.resolve()) + "/"),
        )
        self.render_failed.emit(reason or "viewer render failed")

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True

        page = self.page()
        profile = self.profile
        interceptor = self.interceptor
        channel = self.channel
        bridge = self.bridge

        page.runJavaScript(_DISPOSE_SCRIPT)
        self.startup_timer.stop()
        self.stop()
        if profile is not None:
            profile.setUrlRequestInterceptor(None)
        self._disconnect_load_finished()
        page.setWebChannel(None)
        if channel is not None and bridge is not None:
            channel.deregisterObject(bridge)

        inert_page = QWebEnginePage(self)
        self.setPage(inert_page)

        self.profile = None
        self.interceptor = None
        self.channel = None
        self.bridge = None

        page.deleteLater()
        if bridge is not None:
            bridge.deleteLater()
        if channel is not None:
            channel.deleteLater()
        if interceptor is not None:
            interceptor.deleteLater()
        if profile is not None:
            profile.deleteLater()
