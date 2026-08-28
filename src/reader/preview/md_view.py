from __future__ import annotations

import os
import threading
from pathlib import Path

import PySide6.QtWebChannel  # noqa: F401 - registers :/qtwebchannel/qwebchannel.js
from PySide6.QtCore import QFile, QIODevice, QObject, Property, QTimer, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineSettings,
    QWebEngineUrlRequestInterceptor,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QWidget

from reader.preview.result import PreviewResult
from reader.resources import resource_path

_ALLOWED_NON_FILE_SCHEMES = frozenset({"qrc", "data", "blob"})
_SET_HTML_SAFE_BYTES = 1_900_000
_SAFE_FALLBACK_HTML = (
    "<!doctype html><meta charset='utf-8'>"
    "<p>Markdown 文档无法进行视觉渲染。</p>"
)
_SAFE_FAILURE_MESSAGE = "Markdown 视觉预览不可用，请切换文本模式重试。"


def _install_interceptor(profile, interceptor) -> None:
    profile.setUrlRequestInterceptor(interceptor)


def _canonical_path(path: str | Path) -> str:
    return os.path.normcase(os.path.realpath(os.fspath(path)))


def resolve_wikilink(source: Path, target: str) -> Path | None:
    value = target.strip()
    target_path = Path(value)
    if (
        not value
        or "\x00" in value
        or "/" in value
        or "\\" in value
        or target_path.is_absolute()
        or target_path.suffix.lower() not in {"", ".md"}
        or value in {".", ".."}
    ):
        return None
    source_parent = source.resolve().parent
    name = value if value.lower().endswith(".md") else f"{value}.md"
    candidate = (source_parent / name).resolve()
    if candidate.parent != source_parent or not candidate.is_file():
        return None
    return candidate


class MarkdownBridge(QObject):
    ready = Signal()
    failed = Signal(str)
    open_path = Signal(str)
    missing = Signal(str)

    def __init__(self, source: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._source = source.resolve()
        self._source_url = QUrl.fromLocalFile(str(self._source)).toString(
            QUrl.ComponentFormattingOption.FullyEncoded
        )
        self._active = True

    @Property(str, constant=True)
    def sourceUrl(self) -> str:  # noqa: N802 - WebChannel contract
        return self._source_url

    def deactivate(self) -> None:
        self._active = False

    @Slot(str, result=bool)
    def wikiExists(self, target: str) -> bool:  # noqa: N802 - WebChannel contract
        if not self._active:
            return False
        return resolve_wikilink(self._source, target) is not None

    @Slot(str)
    def openWiki(self, target: str) -> None:  # noqa: N802 - WebChannel contract
        if not self._active:
            return
        resolved = resolve_wikilink(self._source, target)
        if resolved is not None:
            self.open_path.emit(str(resolved))
            return
        self.missing.emit(target[:256])

    @Slot()
    def viewerReady(self) -> None:  # noqa: N802 - WebChannel contract
        if not self._active:
            return
        self.ready.emit()

    @Slot(str)
    def viewerError(self, message: str) -> None:  # noqa: N802 - WebChannel contract
        if not self._active:
            return
        self.failed.emit(message)


class _WebEngineResources(QObject):
    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self.profile: QWebEngineProfile | None = None
        self.page: QWebEnginePage | None = None
        self.channel: QWebChannel | None = None
        self.bridge: MarkdownBridge | None = None
        self.interceptor: OfflineRequestInterceptor | None = None
        self._channel_detached = False
        self._released = False

    def secure_page(self, *, detach_interceptor: bool) -> None:
        if self._released:
            return
        profile = self.profile
        page = self.page
        channel = self.channel
        bridge = self.bridge
        if detach_interceptor and profile is not None:
            _install_interceptor(profile, None)
        if bridge is not None:
            bridge.deactivate()
        if not self._channel_detached:
            if channel is not None and bridge is not None:
                channel.deregisterObject(bridge)
            if page is not None:
                page.setWebChannel(None)
            self._channel_detached = True
        if page is not None:
            page.scripts().clear()
            page.settings().setAttribute(
                QWebEngineSettings.WebAttribute.JavascriptEnabled, False
            )

    @Slot()
    def cleanup(self) -> None:
        if self._released:
            return
        self.secure_page(detach_interceptor=True)
        self.release_detached()

    def release_detached(self) -> None:
        if self._released:
            return
        self._released = True
        objects = (
            self.page,
            self.bridge,
            self.channel,
            self.interceptor,
            self.profile,
        )
        self.page = None
        self.bridge = None
        self.channel = None
        self.interceptor = None
        self.profile = None
        for obj in objects:
            if obj is not None:
                obj.setParent(None)
                obj.deleteLater()
        self.deleteLater()


class OfflineRequestInterceptor(QWebEngineUrlRequestInterceptor):
    """Block any request outside bundle/source directory descendants."""

    def __init__(self, source: Path, bundle_root: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lock = threading.Lock()
        self._blocked: list[str] = []
        self._source_dir = _canonical_path(source.resolve().parent)
        self._bundle_root = _canonical_path(bundle_root)

    @staticmethod
    def _is_within(candidate: str, root: str) -> bool:
        try:
            return os.path.commonpath((candidate, root)) == root
        except ValueError:
            return False

    def _allows_file(self, url: QUrl) -> bool:
        local_file = url.toLocalFile()
        if not local_file:
            return False
        candidate = _canonical_path(local_file)
        return self._is_within(candidate, self._source_dir) or self._is_within(
            candidate, self._bundle_root
        )

    def interceptRequest(self, info) -> None:  # noqa: N802 - Qt virtual method
        url = info.requestUrl()
        scheme = url.scheme().lower()
        if scheme in _ALLOWED_NON_FILE_SCHEMES:
            return
        if scheme == "file" and self._allows_file(url):
            return
        with self._lock:
            self._blocked.append(url.toString())
        info.block(True)

    def blocked_urls(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._blocked)


class MarkdownVisualView(QWebEngineView):
    ready = Signal(int)
    render_failed = Signal(str)
    open_path = Signal(str)
    missing_link = Signal(str)

    def __init__(self, result: PreviewResult, source: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._result = result
        self._source = source.resolve()
        self.started = False
        self.is_fallback = False
        self._shutdown = False
        self._startup_complete = False
        self._load_connected = False
        self._bootstrap_error = False
        self._bootstrap_timer = QTimer(self)
        self._bootstrap_timer.setSingleShot(True)
        self._bootstrap_timer.timeout.connect(self._bootstrap_failed)

        self.viewer_url = QUrl.fromLocalFile(
            str(resource_path("assets", "md-viewer", "index.html").resolve())
        )
        bundle_root = Path(self.viewer_url.toLocalFile()).parent
        self.startup_timer = QTimer(self)
        self.startup_timer.setSingleShot(True)
        self.startup_timer.setInterval(15_000)
        self.startup_timer.timeout.connect(self._startup_timeout)

        app = QApplication.instance()
        if app is None:
            raise RuntimeError("MarkdownVisualView requires QApplication")
        resources = _WebEngineResources(app)
        self._resources: _WebEngineResources | None = resources
        self.destroyed.connect(resources.cleanup)

        self.profile: QWebEngineProfile | None = QWebEngineProfile(app)
        self.interceptor: OfflineRequestInterceptor | None = OfflineRequestInterceptor(
            self._source,
            bundle_root,
            self.profile,
        )
        _install_interceptor(self.profile, self.interceptor)

        page = QWebEnginePage(self.profile, self.profile)
        settings = page.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False
        )

        self.channel: QWebChannel | None = QWebChannel(resources)
        self.bridge: MarkdownBridge | None = MarkdownBridge(self._source, self.channel)
        self.channel.registerObject("bridge", self.bridge)
        page.setWebChannel(self.channel)
        self.setPage(page)
        resources.profile = self.profile
        resources.page = page
        resources.channel = self.channel
        resources.bridge = self.bridge
        resources.interceptor = self.interceptor

        self.loadFinished.connect(self._load_finished)
        self._load_connected = True
        self.bridge.ready.connect(self._viewer_ready)
        self.bridge.failed.connect(self._bridge_failed)
        self.bridge.open_path.connect(self.open_path)
        self.bridge.missing.connect(self.missing_link)

        script_source = self._read_webchannel_script()
        if script_source:
            script = QWebEngineScript()
            script.setName("reader-qwebchannel")
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            script.setRunsOnSubFrames(False)
            script.setSourceCode(script_source)
            page.scripts().insert(script)
        else:
            self._bootstrap_error = True
            self._bootstrap_timer.start(0)

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
        if self.started or self.is_fallback or self._shutdown or self._bootstrap_error:
            return
        self.started = True
        self.startup_timer.start()
        self.load(self.viewer_url)

    @Slot(bool)
    def _load_finished(self, succeeded: bool) -> None:
        if (
            succeeded
            or not self.started
            or self._startup_complete
            or self.is_fallback
            or self._shutdown
        ):
            return
        self._show_fallback()

    @Slot()
    def _startup_timeout(self) -> None:
        if self._startup_complete:
            return
        self._show_fallback()

    @Slot()
    def _bootstrap_failed(self) -> None:
        if self._bootstrap_error:
            self._show_fallback()

    @Slot()
    def _viewer_ready(self) -> None:
        if self._shutdown or self.is_fallback or self._startup_complete:
            return
        self._startup_complete = True
        self.startup_timer.stop()
        self.ready.emit(1)

    @Slot(str)
    def _bridge_failed(self, _message: str) -> None:
        self._show_fallback()

    def _disconnect_load_finished(self) -> None:
        if not self._load_connected:
            return
        try:
            self.loadFinished.disconnect(self._load_finished)
        except (RuntimeError, TypeError):
            pass
        self._load_connected = False

    def _show_fallback(self) -> None:
        if self.is_fallback or self._shutdown:
            return
        self.is_fallback = True
        self.started = False
        self._bootstrap_timer.stop()
        self.startup_timer.stop()
        self._disconnect_load_finished()
        self.stop()
        resources = self._resources
        if resources is not None:
            resources.secure_page(detach_interceptor=True)
        fallback = self._result.fallback_html or _SAFE_FALLBACK_HTML
        if len(fallback.encode("utf-8")) > _SET_HTML_SAFE_BYTES:
            fallback = _SAFE_FALLBACK_HTML
        self.setHtml(fallback, QUrl())
        self.render_failed.emit(_SAFE_FAILURE_MESSAGE)

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self._bootstrap_timer.stop()
        self.startup_timer.stop()
        self.stop()
        self._disconnect_load_finished()
        resources = self._resources
        if resources is not None:
            resources.secure_page(detach_interceptor=True)
        inert_page = QWebEnginePage(self)
        self.setPage(inert_page)
        if resources is not None:
            resources.release_detached()
        self._resources = None
        self.profile = None
        self.interceptor = None
        self.channel = None
        self.bridge = None

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt virtual method
        self.shutdown()
        super().closeEvent(event)

