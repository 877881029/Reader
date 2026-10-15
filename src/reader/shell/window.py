from __future__ import annotations

import ctypes
import os
import shutil
import tempfile
import threading
from collections.abc import Callable
from ctypes import wintypes
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from PySide6.QtCore import QEvent, QObject, QPoint, QRunnable, QThreadPool, QTimer, QUrl, Qt, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QIcon,
    QKeySequence,
    QResizeEvent,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from reader.formats.binary import BINARY_SUFFIXES
from reader.formats.code import CODE_SUFFIXES
from reader.formats.image import IMAGE_SUFFIXES
from reader.open import decide_open
from reader.preview.cache import PreviewCache
from reader.preview.office import Win32OfficeBackend
from reader.preview.pipeline import PreviewMode, preview
from reader.preview.result import PreviewResult
from reader.preview.find_support import (
    clear_find_highlights,
    find_in_widget,
    replace_all,
    replace_current,
    resolve_find_target,
)
from reader.resources import resource_path
from reader.theme import MUTED, PAPER as PAGE_FILL
from reader.shell.find_bar import FindBar
from reader.shell.goto_bar import GotoLineBar
from reader.shell.recent import remember_recent
from reader.shell.tab_drag import ReaderTabBar
from reader.shell.taskbar import apply_hwnd_app_user_model, force_iconic_representation
from reader.shell.title_chrome import TitleChrome, hit_test_local, lparam_to_local
from reader.shell.welcome import WelcomePage
from reader.smoke import (
    append_document_ready,
    append_markdown_ready,
    append_visual_ready,
)

MARKDOWN_PUSH_DELAY_MS = 150
# Where the cursor sits on a torn-off window: over its first tab.
TEAR_OFF_GRAB = QPoint(120, 18)
MARKDOWN_PRECREATE_DELAY_MS = 300
WM_NCHITTEST = 0x0084
WM_NCCALCSIZE = 0x0083
GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_SYSMENU = 0x00080000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020
WM_SETICON = 0x0080
ICON_SMALL = 0
ICON_BIG = 1
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
SM_CXICON = 11
SM_CYICON = 12
SM_CXSMICON = 49
SM_CYSMICON = 50
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2


class ChromeTabWidget(QTabWidget):
    """QTabWidget that does not keep a ghost tab-bar gap after the bar is reparented."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTabBar(ReaderTabBar(self))
        self._resize_stretch_timer = QTimer(self)
        self._resize_stretch_timer.setSingleShot(True)
        self._resize_stretch_timer.setInterval(16)
        self._resize_stretch_timer.timeout.connect(self._stretch_pane)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._resize_stretch_timer.start()

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self._stretch_pane()
        QTimer.singleShot(0, self, self._stretch_pane)

    def tabInserted(self, index: int) -> None:  # noqa: N802
        super().tabInserted(index)
        self._stretch_pane()

    def event(self, event: QEvent) -> bool:
        handled = super().event(event)
        if event.type() == QEvent.Type.LayoutRequest:
            self._stretch_pane()
        return handled

    def _stretch_pane(self) -> None:
        try:
            stack = self.findChild(QStackedWidget, "qt_tabwidget_stackedwidget")
        except RuntimeError:
            return
        if stack is None:
            return
        target = self.rect()
        if target.width() <= 0 or target.height() <= 0:
            return
        if stack.geometry() == target:
            return
        stack.setGeometry(target)

PreviewFunction = Callable[..., PreviewResult]
CacheFactory = Callable[[], PreviewCache]
ViewerFactory = Callable[[PreviewResult, Path], QWidget]
OFFICE_SUFFIXES = {".docx", ".pptx", ".xlsx"}
_OFFICE_AVAILABILITY_CACHE: dict[tuple[object, str], bool] = {}
_OFFICE_AVAILABILITY_LOCK = threading.Lock()


@dataclass(frozen=True)
class _WorkerOutput:
    result: PreviewResult
    artifact_dir: Path | None = None


def _cleanup_dir(path: Path | None) -> None:
    if path is not None:
        shutil.rmtree(path, ignore_errors=True)


def _source_owns_pdf(result: PreviewResult) -> bool:
    if result.asset_dir is None or result.pdf_path is None:
        return False
    try:
        result.pdf_path.resolve().relative_to(result.asset_dir.resolve())
    except (OSError, ValueError):
        return False
    return True


def _pin_pdf(result: PreviewResult, source_path: Path | None = None) -> _WorkerOutput:
    if result.kind == "html" and result.asset_dir is not None:
        return _WorkerOutput(result, result.asset_dir)
    if result.kind != "pdf" or result.pdf_path is None:
        return _WorkerOutput(result)
    if source_path is not None and result.pdf_path.resolve() == Path(source_path).resolve():
        return _WorkerOutput(result)

    source_asset_dir = result.asset_dir if _source_owns_pdf(result) else None
    artifact_dir = Path(tempfile.mkdtemp(prefix="reader-document-"))
    pinned_pdf = artifact_dir / "preview.pdf"
    try:
        shutil.copy2(result.pdf_path, pinned_pdf)
    except Exception:
        _cleanup_dir(artifact_dir)
        _cleanup_dir(source_asset_dir)
        raise

    pinned = replace(result, pdf_path=pinned_pdf, asset_dir=artifact_dir)
    if source_asset_dir is not None:
        _cleanup_dir(source_asset_dir)
    return _WorkerOutput(pinned, artifact_dir)


class _WorkerSignals(QObject):
    completed = Signal(str, object, object)


class _AvailabilitySignals(QObject):
    completed = Signal(str, object)


class _AvailabilityWorker(QRunnable):
    def __init__(
        self,
        request_id: str,
        suffix: str,
        office: Win32OfficeBackend,
        signals: _AvailabilitySignals,
    ) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self.request_id = request_id
        self.suffix = suffix
        self.office = office
        self.signals = signals

    @Slot()
    def run(self) -> None:
        if type(self.office) is Win32OfficeBackend:
            cache_key = (Win32OfficeBackend, self.suffix)
            with _OFFICE_AVAILABILITY_LOCK:
                available = _OFFICE_AVAILABILITY_CACHE.get(cache_key)
                if available is None:
                    try:
                        available = self.office.available_for(self.suffix)
                    except Exception:
                        available = False
                    _OFFICE_AVAILABILITY_CACHE[cache_key] = available
        else:
            try:
                available = self.office.available_for(self.suffix)
            except Exception:
                available = False
        self.signals.completed.emit(self.request_id, available)


class _PreviewWorker(QRunnable):
    def __init__(
        self,
        document_id: str,
        path: Path,
        preview_fn: PreviewFunction,
        office: Win32OfficeBackend,
        cache_factory: CacheFactory,
        signals: _WorkerSignals,
        mode: PreviewMode,
    ) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self.document_id = document_id
        self.path = path
        self.preview_fn = preview_fn
        self.office = office
        self.cache_factory = cache_factory
        self.signals = signals
        self.mode = mode

    @Slot()
    def run(self) -> None:
        result: PreviewResult | None = None
        try:
            suffix = self.path.suffix.lower()
            visual_suffix = suffix in {".pptx", ".md"}
            strategy = (
                "visual"
                if visual_suffix and self.mode in {"builtin", "visual"}
                else self.mode
            )
            cache: PreviewCache | None
            cache = None
            if (
                strategy != "visual"
                and suffix != ".pdf"
                and suffix != ".svg"
                and suffix not in IMAGE_SUFFIXES
                and suffix not in CODE_SUFFIXES
                and suffix not in BINARY_SUFFIXES
            ):
                try:
                    cache = self.cache_factory()
                    result = cache.get(self.path, strategy)
                except Exception:
                    cache = None

            if result is None:
                result = self.preview_fn(self.path, office=self.office, mode=self.mode)
                cacheable = not (
                    (result.kind == "html" and result.asset_dir is not None)
                    or (
                        result.kind == "pdf"
                        and result.pdf_path is not None
                        and result.pdf_path.resolve() == self.path.resolve()
                    )
                    or (
                        result.kind == "svg"
                        and result.svg_path is not None
                        and result.svg_path.resolve() == self.path.resolve()
                    )
                    or (
                        result.kind == "image"
                        and result.image_path is not None
                        and result.image_path.resolve() == self.path.resolve()
                    )
                )
                if cache is not None and cacheable:
                    try:
                        cache.put(self.path, strategy, result)
                    except Exception:
                        pass
            output = _pin_pdf(result, self.path)
        except Exception as exc:
            self.signals.completed.emit(self.document_id, None, exc)
            return
        self.signals.completed.emit(self.document_id, output, None)


class PreviewExecutor(QObject):
    completed = Signal(str)
    availability_completed = Signal(str, object)

    def __init__(
        self,
        *,
        thread_pool: QThreadPool | None = None,
        availability_thread_pool: QThreadPool | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.thread_pool = thread_pool or QThreadPool(self)
        self.thread_pool.setMaxThreadCount(1)
        self.availability_thread_pool = availability_thread_pool or QThreadPool(self)
        self.availability_thread_pool.setMaxThreadCount(1)
        self._workers: dict[str, _PreviewWorker] = {}
        self._availability_workers: dict[str, _AvailabilityWorker] = {}
        self._pending: dict[
            str, tuple[_WorkerOutput | None, Exception | None]
        ] = {}
        self._cancelled: set[str] = set()
        self._owner_registry: list[PreviewExecutor] | None = None
        self._release_requested = False

    def submit(
        self,
        document_id: str,
        path: Path,
        preview_fn: PreviewFunction,
        office: Win32OfficeBackend,
        cache_factory: CacheFactory,
        mode: PreviewMode = "builtin",
    ) -> None:
        signals = _WorkerSignals(self)
        worker = _PreviewWorker(
            document_id,
            path,
            preview_fn,
            office,
            cache_factory,
            signals,
            mode,
        )
        signals.completed.connect(
            self._worker_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self._workers[document_id] = worker
        self.thread_pool.start(worker)

    def probe_office(
        self,
        request_id: str,
        suffix: str,
        office: Win32OfficeBackend,
    ) -> None:
        signals = _AvailabilitySignals(self)
        worker = _AvailabilityWorker(request_id, suffix, office, signals)
        signals.completed.connect(
            self._availability_worker_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self._availability_workers[request_id] = worker
        self.availability_thread_pool.start(worker)

    def cancel(self, document_id: str) -> None:
        if document_id in self._workers:
            self._cancelled.add(document_id)
        if document_id in self._availability_workers:
            self._cancelled.add(document_id)
        pending = self._pending.pop(document_id, None)
        if pending is not None:
            output, _error = pending
            if output is not None:
                _cleanup_dir(output.artifact_dir)
        self._release_if_idle()

    def take_completion(
        self, document_id: str
    ) -> tuple[_WorkerOutput | None, Exception | None] | None:
        completion = self._pending.pop(document_id, None)
        self._release_if_idle()
        return completion

    def active_count(self) -> int:
        return (
            len(self._workers)
            + len(self._availability_workers)
            + len(self._pending)
        )

    def is_running(self, request_id: str) -> bool:
        return request_id in self._workers

    def set_owner_registry(self, registry: list[PreviewExecutor]) -> None:
        self._owner_registry = registry

    def release_when_idle(self) -> None:
        self._release_requested = True
        self._release_if_idle()

    def _release_if_idle(self) -> None:
        if not self._release_requested or self.active_count() != 0:
            return
        if self._owner_registry is not None:
            try:
                self._owner_registry.remove(self)
            except ValueError:
                pass
            self._owner_registry = None
        self._release_requested = False
        self.deleteLater()

    @Slot(str, object, object)
    def _worker_completed(
        self,
        document_id: str,
        output: _WorkerOutput | None,
        error: Exception | None,
    ) -> None:
        worker = self._workers.pop(document_id, None)
        cancelled = document_id in self._cancelled
        self._cancelled.discard(document_id)

        if cancelled:
            if output is not None:
                _cleanup_dir(output.artifact_dir)
        else:
            self._pending[document_id] = (output, error)
            self.completed.emit(document_id)

        if worker is not None:
            worker.signals.deleteLater()
            del worker
        self._release_if_idle()

    @Slot(str, object)
    def _availability_worker_completed(
        self,
        request_id: str,
        available: bool,
    ) -> None:
        worker = self._availability_workers.pop(request_id, None)
        cancelled = request_id in self._cancelled
        self._cancelled.discard(request_id)
        if not cancelled:
            self.availability_completed.emit(request_id, available)
        if worker is not None:
            worker.signals.deleteLater()
            del worker
        self._release_if_idle()


@dataclass
class _Document:
    path: Path
    page: QWidget
    artifact_dir: Path | None = None
    builtin_artifact_dir: Path | None = None
    mode: PreviewMode = "builtin"
    builtin_mode: Literal["builtin", "visual", "text"] = "builtin"
    last_result: PreviewResult | None = None
    office_available: bool | None = None
    status_label: str = "正在加载…"
    generation: int = 0
    visual_slide_count: int | None = None
    visual_slide_index: int | None = None
    visual_widget: QWidget | None = None
    visual_connections: list[tuple[Any, Callable[..., None]]] = field(
        default_factory=list
    )
    request_id: str | None = None
    availability_request_id: str | None = None
    office_requested: bool = False
    # Seamless Markdown editing: the hidden counterpart of the visible view.
    md_preview: QWidget | None = None
    md_preview_result: PreviewResult | None = None
    md_editor: QWidget | None = None
    md_push_timer: QTimer | None = None


def _directory_url(path: Path) -> QUrl:
    return QUrl.fromLocalFile(str(path.resolve()) + os.sep)


def _html_base_url(result: PreviewResult, source_path: Path) -> QUrl:
    return _directory_url(result.asset_dir or source_path.parent)


def _default_viewer(result: PreviewResult, source_path: Path) -> QWidget:
    if result.kind == "pptx":
        from reader.preview.pptx_view import PptxVisualView

        return PptxVisualView(result, source_path)
    if result.kind == "markdown":
        from reader.preview.md_view import MarkdownVisualView

        return MarkdownVisualView(result, source_path)
    if result.kind == "code":
        from reader.preview.code_view import CodeTextView

        view = CodeTextView()
        if source_path.is_file():
            view.load_path(source_path)
        else:
            view.load_text(result.html, source_path.suffix)
        return view
    if result.kind == "svg":
        from reader.preview.svg_view import SvgView

        view = SvgView()
        view.load_path(result.svg_path or source_path)
        return view
    if result.kind == "binary":
        from reader.preview.hex_view import HexView

        view = HexView()
        view.load_path(result.binary_path or source_path)
        return view
    if result.kind == "image":
        from reader.preview.image_view import ImageView

        view = ImageView()
        view.load_path(result.image_path or source_path)
        return view

    from PySide6.QtWebEngineCore import QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView

    web = QWebEngineView()
    web.page().setBackgroundColor(QColor(PAGE_FILL))
    if result.kind == "pdf" and result.pdf_path is not None:
        settings = web.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
        web.load(QUrl.fromLocalFile(str(result.pdf_path)))
    else:
        web.setHtml(result.html, _html_base_url(result, source_path))
    return web


def _retire_widget(widget: QWidget) -> None:
    """Remove replaced content: keep it hidden if marked to be kept, else dispose."""
    widget.setProperty("readerRetiring", False)
    if widget.property("readerKeepOnRetire") is True:
        widget.setProperty("readerKeepOnRetire", False)
        widget.hide()
        return
    _dispose_widget(widget)


def _dispose_widget(widget: QWidget) -> None:
    try:
        shutdown = getattr(widget, "shutdown", None)
        if callable(shutdown):
            shutdown()
    finally:
        widget.setParent(None)
        widget.deleteLater()


class MainWindow(QMainWindow):
    DEFAULT_SIZE = (1200, 640)
    MINIMUM_SIZE = (800, 400)

    def __init__(
        self,
        on_new_window: Callable[[], MainWindow] | None = None,
        *,
        on_closing: Callable[[MainWindow], None] | None = None,
        on_activated: Callable[[MainWindow], None] | None = None,
        preview_fn: PreviewFunction = preview,
        cache_factory: CacheFactory = PreviewCache,
        viewer_factory: ViewerFactory | None = None,
        executor: PreviewExecutor | None = None,
        thread_pool: QThreadPool | None = None,
        office: Win32OfficeBackend | None = None,
        icon_path_provider: Callable[[], Path] | None = None,
        icon_applier: Callable[[QIcon], None] | None = None,
        unsaved_prompt: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__()
        self.unsaved_prompt: Callable[[str], str] | None = unsaved_prompt

        self.setWindowTitle("Reader")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.resize(*self.DEFAULT_SIZE)
        self.setMinimumSize(*self.MINIMUM_SIZE)
        icon_path = (
            icon_path_provider() if icon_path_provider is not None else _window_icon_path()
        )
        self._icon_path = icon_path
        self._native_icon_handles: tuple[int, int] | None = None
        self._taskbar_iconic_forced = False
        _load_icon_if_exists(icon_path, icon_applier or self.setWindowIcon)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setAcceptDrops(True)

        self._on_new_window = on_new_window
        self._on_closing = on_closing
        self._on_activated = on_activated
        self._preview_fn = preview_fn
        self._cache_factory = cache_factory
        self._viewer_factory = viewer_factory or _default_viewer
        self._office = office or Win32OfficeBackend()
        app = QApplication.instance()
        self._owns_executor = executor is None
        if executor is None:
            self._executor = PreviewExecutor(
                thread_pool=thread_pool,
                parent=app,
            )
            if app is not None:
                owners = getattr(app, "_reader_preview_executors", None)
                if owners is None:
                    owners = []
                    setattr(app, "_reader_preview_executors", owners)
                owners.append(self._executor)
                self._executor.set_owner_registry(owners)
        else:
            self._executor = executor
        self._executor.completed.connect(
            self._preview_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self._executor.availability_completed.connect(
            self._office_availability_completed,
        )
        self._documents: dict[str, _Document] = {}
        self._requests: dict[
            str, tuple[str, int, PreviewMode, PreviewMode, str]
        ] = {}
        self._availability_requests: dict[str, tuple[str, int]] = {}
        self._owned_request_ids: set[str] = set()
        self._closing = False
        self._welcome_allowed = False
        self._opened_files_before_show = False

        self._tabs = ChromeTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.tabCloseRequested.connect(self.close_tab)
        self._tabs.setDocumentMode(True)
        self._tabs.setAcceptDrops(True)
        self._tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{
                border: none;
                margin: 0px;
                padding: 0px;
                top: 0px;
                background: {PAGE_FILL};
            }}
            """
        )

        self._title_chrome = TitleChrome(self)
        self._title_chrome.set_window_icon(self.windowIcon())
        self._title_chrome.adopt_tab_bar(self._tabs.tabBar())
        self._tabs.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tabs.tabBar().customContextMenuRequested.connect(self._show_tab_menu)
        self._tabs.tabBar().detach_finished.connect(
            lambda index, pos: self._finish_tab_drag(index, pos)
        )
        self._tabs._stretch_pane()
        self._title_chrome.minimize_requested.connect(self.showMinimized)
        self._title_chrome.maximize_requested.connect(self._toggle_maximize)
        self._title_chrome.close_requested.connect(self.close)
        self._title_chrome.update_maximize_state(self.isMaximized())

        self._welcome = WelcomePage()
        self._welcome.open_requested.connect(self._open_dialog)
        self._welcome.new_markdown_requested.connect(self.add_untitled_markdown_tab)
        self._welcome.recent_opened.connect(lambda path: self.open_paths([path]))

        self._content_stack = QStackedWidget()
        self._content_stack.setObjectName("contentStack")
        self._content_stack.setAcceptDrops(True)
        self._content_stack.setStyleSheet(f"#contentStack {{ background: {PAGE_FILL}; }}")
        self._content_stack.addWidget(self._welcome)
        self._content_stack.addWidget(self._tabs)

        container = QWidget(self)
        container.setObjectName("readerRoot")
        container.setAcceptDrops(True)
        container.setStyleSheet(f"#readerRoot {{ background: {PAGE_FILL}; }}")
        root = QVBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._find_bar = FindBar()
        self._find_bar.next_requested.connect(lambda: self._find_step(True))
        self._find_bar.previous_requested.connect(lambda: self._find_step(False))
        self._find_bar.hide_requested.connect(self._hide_find_bar)
        self._find_bar.replace_requested.connect(self._replace_step)
        self._find_bar.replace_all_requested.connect(self._replace_all)

        root.addWidget(self._title_chrome)
        root.addWidget(self._find_bar)
        self._goto_bar = GotoLineBar()
        self._goto_bar.submitted.connect(self._goto_submitted)
        self._goto_bar.hide_requested.connect(self._hide_goto_bar)
        root.addWidget(self._goto_bar)
        root.addWidget(self._content_stack, 1)
        self.setCentralWidget(container)
        status = QStatusBar()
        status.setObjectName("readerStatusBar")
        status.setSizeGripEnabled(False)
        status.setMaximumHeight(0)
        status.hide()
        self.setStatusBar(status)
        self._hide_status_bar()

        self.actionOpen = QAction("打开", self)
        self.actionOpen.setObjectName("actionOpen")
        self.actionOpen.setShortcut(QKeySequence.StandardKey.Open)
        self.actionOpen.triggered.connect(self._open_dialog)
        self.addAction(self.actionOpen)

        self.actionNewTab = QAction("+", self)
        self.actionNewTab.setObjectName("actionNewTab")
        self.actionNewTab.triggered.connect(self.add_blank_tab)
        self.addAction(self.actionNewTab)
        self._build_new_tab_menu()

        self.actionNewWindow = QAction("新建窗口", self)
        self.actionNewWindow.setObjectName("actionNewWindow")
        self.actionNewWindow.triggered.connect(self._spawn)
        self.addAction(self.actionNewWindow)

        self.actionOfficePreview = QAction("Office 高保真", self)
        self.actionOfficePreview.setObjectName("actionOfficePreview")
        self.actionOfficePreview.triggered.connect(self.switch_current_tab_to_office)
        self.addAction(self.actionOfficePreview)

        self.actionBuiltinPreview = QAction("内置预览", self)
        self.actionBuiltinPreview.setObjectName("actionBuiltinPreview")
        self.actionBuiltinPreview.triggered.connect(self.switch_current_tab_to_builtin)
        self.addAction(self.actionBuiltinPreview)

        self.actionTextPreview = QAction("文本模式", self)
        self.actionTextPreview.setObjectName("actionTextPreview")
        self.actionTextPreview.triggered.connect(self.switch_current_tab_to_text)
        self.addAction(self.actionTextPreview)

        self.actionVisualPreview = QAction("视觉模式", self)
        self.actionVisualPreview.setObjectName("actionVisualPreview")
        self.actionVisualPreview.triggered.connect(self.switch_current_tab_to_visual)
        self.addAction(self.actionVisualPreview)

        self.actionMarkdownEdit = QAction("Markdown 编辑", self)
        self.actionMarkdownEdit.setObjectName("actionMarkdownEdit")
        self.actionMarkdownEdit.setShortcut(QKeySequence("Ctrl+I"))
        self.actionMarkdownEdit.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.actionMarkdownEdit.triggered.connect(self._shortcut_markdown_edit)
        self.addAction(self.actionMarkdownEdit)

        self.actionMarkdownPreview = QAction("Markdown 渲染", self)
        self.actionMarkdownPreview.setObjectName("actionMarkdownPreview")
        self.actionMarkdownPreview.setShortcut(QKeySequence("Ctrl+T"))
        self.actionMarkdownPreview.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.actionMarkdownPreview.triggered.connect(self._shortcut_markdown_preview)
        self.addAction(self.actionMarkdownPreview)
        self._title_chrome.markdown_mode_requested.connect(self._on_markdown_mode_requested)

        self.actionSave = QAction("保存", self)
        self.actionSave.setObjectName("actionSave")
        self.actionSave.setShortcut(QKeySequence.StandardKey.Save)
        self.actionSave.triggered.connect(self.save_current_tab)
        self.addAction(self.actionSave)
        self.actionSaveAs = QAction("另存为", self)
        self.actionSaveAs.setObjectName("actionSaveAs")
        self.actionSaveAs.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.actionSaveAs.triggered.connect(self.save_current_tab_as)
        self.addAction(self.actionSaveAs)
        self.actionNewText = QAction("新建文本", self)
        self.actionNewText.setObjectName("actionNewText")
        self.actionNewText.setShortcut(QKeySequence.StandardKey.New)
        self.actionNewText.triggered.connect(self.add_untitled_text_tab)
        self.addAction(self.actionNewText)

        self.actionFind = QAction("查找", self)
        self.actionFind.setObjectName("actionFind")
        self.actionFind.setShortcut(QKeySequence.StandardKey.Find)
        self.actionFind.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.actionFind.triggered.connect(self._shortcut_find)
        self.addAction(self.actionFind)

        self.actionReplace = QAction("替换", self)
        self.actionReplace.setObjectName("actionReplace")
        self.actionReplace.setShortcut(QKeySequence("Ctrl+H"))
        self.actionReplace.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.actionReplace.triggered.connect(self._shortcut_replace)
        self.addAction(self.actionReplace)

        self.actionGoToLine = QAction("转到行", self)
        self.actionGoToLine.setObjectName("actionGoToLine")
        self.actionGoToLine.setShortcuts([QKeySequence("Ctrl+J"), QKeySequence("Ctrl+G")])
        self.actionGoToLine.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.actionGoToLine.triggered.connect(self._shortcut_goto_line)
        self.addAction(self.actionGoToLine)

        self.actionFindNext = QAction("查找下一个", self)
        self.actionFindNext.setObjectName("actionFindNext")
        self.actionFindNext.setShortcut(QKeySequence.StandardKey.FindNext)
        self.actionFindNext.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.actionFindNext.triggered.connect(lambda: self._shortcut_find_step(True))
        self.addAction(self.actionFindNext)

        self.actionFindPrevious = QAction("查找上一个", self)
        self.actionFindPrevious.setObjectName("actionFindPrevious")
        self.actionFindPrevious.setShortcut(QKeySequence.StandardKey.FindPrevious)
        self.actionFindPrevious.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.actionFindPrevious.triggered.connect(lambda: self._shortcut_find_step(False))
        self.addAction(self.actionFindPrevious)

        self.actionFindClose = QAction("关闭查找", self)
        self.actionFindClose.setObjectName("actionFindClose")
        self.actionFindClose.setShortcut(QKeySequence(Qt.Key.Key_Escape))
        self.actionFindClose.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.actionFindClose.triggered.connect(self._hide_find_bar)
        self.actionFindClose.setEnabled(False)
        self.addAction(self.actionFindClose)

        self.menuBar().clear()
        self.menuBar().setVisible(False)
        self.menuBar().setMaximumHeight(0)

        self._tabs.currentChanged.connect(self._refresh_preview_actions)
        self._refresh_preview_actions()
        self._refresh_content_stack()
        self._ensure_win32_frame_styles()

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 - Qt API
        super().showEvent(event)
        if self._tabs.count() == 0 and not self._opened_files_before_show:
            self._welcome_allowed = True
        self._ensure_win32_frame_styles()
        self._hide_status_bar()
        self._tabs._stretch_pane()
        QTimer.singleShot(0, self._tabs, self._tabs._stretch_pane)
        QTimer.singleShot(0, self, self._reapply_native_window_icons)
        QTimer.singleShot(80, self, self._reapply_native_window_icons)

    def _hide_status_bar(self) -> None:
        bar = self.statusBar()
        bar.setSizeGripEnabled(False)
        bar.setMaximumHeight(0)
        bar.hide()

    def _ensure_win32_frame_styles(self) -> None:
        if os.name != "nt":
            return
        hwnd = int(self.winId())
        if hwnd == 0:
            return
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
        wanted = (
            WS_CAPTION
            | WS_THICKFRAME
            | WS_MINIMIZEBOX
            | WS_MAXIMIZEBOX
            | WS_SYSMENU
        )
        if style & wanted != wanted:
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style | wanted)
            ctypes.windll.user32.SetWindowPos(
                hwnd,
                0,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
            )
        self._apply_rounded_corners(hwnd)
        self._apply_native_window_icons(hwnd)
        self._tabs._stretch_pane()

    def _reapply_native_window_icons(self) -> None:
        if os.name != "nt":
            return
        hwnd = int(self.winId())
        self._apply_native_window_icons(hwnd)

    def _apply_native_window_icons(self, hwnd: int) -> None:
        if os.name != "nt" or hwnd == 0:
            return
        icon_path = getattr(self, "_icon_path", None)
        if icon_path is None or not Path(icon_path).exists():
            return
        handles = self._native_icon_handles
        if handles is None:
            user32 = ctypes.windll.user32
            small = _load_native_icon(
                Path(icon_path),
                user32.GetSystemMetrics(SM_CXSMICON),
                user32.GetSystemMetrics(SM_CYSMICON),
            )
            big = _load_native_icon(
                Path(icon_path),
                user32.GetSystemMetrics(SM_CXICON),
                user32.GetSystemMetrics(SM_CYICON),
            )
            if small == 0 and big == 0:
                return
            handles = (small, big)
            self._native_icon_handles = handles
        small, big = handles
        if small:
            _send_message_w(hwnd, WM_SETICON, ICON_SMALL, small)
        if big:
            _send_message_w(hwnd, WM_SETICON, ICON_BIG, big)
        self._taskbar_iconic_forced = force_iconic_representation(hwnd)
        apply_hwnd_app_user_model(hwnd, Path(icon_path))

    def _apply_rounded_corners(self, hwnd: int) -> None:
        try:
            preference = ctypes.c_int(DWMWCP_ROUND)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(preference),
                ctypes.sizeof(preference),
            )
        except Exception:
            return

    def _tab_has_preview_content(self, page: QWidget | None) -> bool:
        if page is None:
            return False
        layout = page.layout()
        if layout is None:
            return False
        for index in range(layout.count()):
            widget = layout.itemAt(index).widget()
            if widget is None or widget.objectName() == "previewLoading":
                continue
            if widget.property("readerPreviewReady") is False:
                continue
            return True
        return False

    def _arm_preview_ready(self, content: QWidget) -> None:
        if getattr(content, "ready", None) is not None:
            is_ready = getattr(content, "is_ready", None)
            if callable(is_ready) and is_ready():
                content.setProperty("readerPreviewReady", True)
                return
            content.setProperty("readerPreviewReady", False)
            content.hide()
            return
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
        except Exception:
            content.setProperty("readerPreviewReady", True)
            return
        if isinstance(content, QWebEngineView):
            content.setProperty("readerPreviewReady", False)
            content.hide()
            content.loadFinished.connect(
                lambda _ok, widget=content: self._mark_preview_ready(widget)
            )
            return
        content.setProperty("readerPreviewReady", True)

    def _mark_preview_ready(self, widget: QWidget) -> None:
        try:
            widget.setProperty("readerPreviewReady", True)
            widget.show()
            owner = widget.window()
        except RuntimeError:
            return
        self._retire_previous_content(widget)
        # The tab may have moved to another window while it was loading.
        (owner if isinstance(owner, MainWindow) else self)._refresh_content_stack()

    def _retire_previous_content(self, widget: QWidget) -> None:
        try:
            page = widget.parentWidget()
            layout = page.layout() if page is not None else None
        except RuntimeError:
            return
        if layout is None or layout.indexOf(widget) < 0:
            return
        for index in range(layout.count() - 1, -1, -1):
            other = layout.itemAt(index).widget()
            if other is None or other is widget:
                continue
            if other.property("readerRetiring") is True:
                layout.takeAt(index)
                _retire_widget(other)

    def _refresh_content_stack(self) -> None:
        stack = getattr(self, "_content_stack", None)
        if stack is None:
            return
        has_tabs = self._tabs.count() > 0
        has_content = any(
            self._tab_has_preview_content(self._tabs.widget(index))
            for index in range(self._tabs.count())
        )
        if not has_tabs:
            if self.isVisible():
                self._welcome_allowed = True
            stack.setCurrentIndex(0)
            self._welcome.reload_recent()
            self._hide_find_bar()
            return
        if has_content or not self._welcome_allowed:
            stack.setCurrentIndex(1)
            return
        stack.setCurrentIndex(0)
        self._welcome.reload_recent()
        self._hide_find_bar()

    def event(self, event: QEvent) -> bool:
        if (
            event.type() == QEvent.Type.WindowActivate
            and not getattr(self, "_closing", True)
        ):
            callback = getattr(self, "_on_activated", None)
            if callback is not None:
                callback(self)
        if event.type() == QEvent.Type.WindowStateChange:
            chrome = getattr(self, "_title_chrome", None)
            if chrome is not None:
                chrome.update_maximize_state(self.isMaximized())
        return super().event(event)

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def nativeEvent(self, eventType, message):  # noqa: N802 - Qt API
        if os.name == "nt" and eventType in (b"windows_generic_MSG", "windows_generic_MSG"):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_NCHITTEST:
                x = ctypes.c_int16(msg.lParam & 0xFFFF).value
                y = ctypes.c_int16((msg.lParam >> 16) & 0xFFFF).value
                local = lparam_to_local(self, x, y)
                return True, hit_test_local(self, local)
            if msg.message == WM_NCCALCSIZE and msg.wParam:
                return True, 0
        return super().nativeEvent(eventType, message)

    def center_on_screen(self, offset: int = 0) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        frame.moveTopLeft(frame.topLeft() + QPoint(offset, offset))
        self.move(frame.topLeft())

    def _spawn(self) -> None:
        if self._on_new_window is not None:
            self._on_new_window()

    def tab_count(self) -> int:
        return self._tabs.count()

    def tab_title(self, index: int) -> str:
        return self._tabs.tabText(index)

    def find_bar(self) -> FindBar:
        return self._find_bar

    def _current_preview_widget(self) -> QWidget | None:
        page = self._tabs.currentWidget()
        if page is None:
            return None
        layout = page.layout()
        if layout is None:
            return None
        for index in range(layout.count()):
            widget = layout.itemAt(index).widget()
            if widget is not None and widget.objectName() != "previewLoading":
                return widget
        return None

    def _welcome_visible(self) -> bool:
        stack = getattr(self, "_content_stack", None)
        welcome = getattr(self, "_welcome", None)
        if stack is None or welcome is None:
            return False
        return self.tab_count() == 0 and stack.currentWidget() is welcome

    def _shortcut_find(self) -> None:
        if self._welcome_visible():
            self._welcome.show_lookup()
            self.actionFindClose.setEnabled(True)
            return
        if self._current_preview_widget() is None:
            return
        self._hide_goto_bar()
        self._find_bar.set_replace_mode(False)
        self._find_bar.show()
        self.actionFindClose.setEnabled(True)
        self._find_bar.focus_query()

    def _writable_text_editor(self) -> QPlainTextEdit | None:
        document_id = self._current_document_id()
        document = self._documents.get(document_id) if document_id else None
        view = self._editable_view(document)
        if view is None or (document is not None and view.objectName() == "markdownTextView" and document.mode != "text"):
            return None
        editor = resolve_find_target(view)
        if not isinstance(editor, QPlainTextEdit) or editor.isReadOnly():
            return None
        return editor

    def _goto_target(self) -> QPlainTextEdit | None:
        editor = resolve_find_target(self._current_preview_widget())
        return editor if isinstance(editor, QPlainTextEdit) else None

    def _shortcut_goto_line(self) -> None:
        editor = self._goto_target()
        if editor is None:
            return
        if self._find_bar.isVisible():
            self._hide_find_bar()
        self._goto_bar.open(max(editor.document().blockCount(), 1))

    def _goto_submitted(self, text: str) -> None:
        editor = self._goto_target()
        if editor is None:
            self._hide_goto_bar()
            return
        try:
            line = int(text.strip())
        except ValueError:
            self._goto_bar.set_message("无效行号")
            return
        document = editor.document()
        maximum = max(document.blockCount(), 1)
        block = document.findBlockByNumber(min(max(line, 1), maximum) - 1)
        cursor = editor.textCursor()
        cursor.setPosition(block.position())
        editor.setTextCursor(cursor)
        editor.centerCursor()
        self._hide_goto_bar()
        editor.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _hide_goto_bar(self) -> None:
        bar = getattr(self, "_goto_bar", None)
        if bar is None:
            return
        bar.set_message("")
        bar.hide()
    def _shortcut_replace(self) -> None:
        if self._writable_text_editor() is None:
            return
        self._hide_goto_bar()
        self._find_bar.set_replace_mode(True)
        self._find_bar.set_not_found(False)
        self._find_bar.show()
        self.actionFindClose.setEnabled(True)
        self._find_bar.focus_query()

    def _replace_step(self) -> None:
        editor = self._writable_text_editor()
        query = self._find_bar.query()
        if editor is None or not query:
            return
        found = replace_current(
            editor,
            query,
            self._find_bar.replacement(),
            case_sensitive=self._find_bar.match_case(),
        )
        self._find_bar.set_not_found(not found)

    def _replace_all(self) -> None:
        editor = self._writable_text_editor()
        query = self._find_bar.query()
        if editor is None or not query:
            return
        count = replace_all(
            editor,
            query,
            self._find_bar.replacement(),
            case_sensitive=self._find_bar.match_case(),
        )
        self._find_bar.set_message(f"已替换 {count} 处" if count else "未找到")

    def _shortcut_find_step(self, forward: bool) -> None:
        if self._current_preview_widget() is None:
            return
        if not self._find_bar.query():
            self._shortcut_find()
            return
        self._find_bar.show()
        self.actionFindClose.setEnabled(True)
        self._find_step(forward)

    def _find_step(self, forward: bool) -> None:
        query = self._find_bar.query()
        if not query:
            self._find_bar.set_not_found(False)
            return
        find_in_widget(
            self._current_preview_widget(),
            query,
            forward=forward,
            case_sensitive=self._find_bar.match_case(),
            on_result=lambda found: self._find_bar.set_not_found(not found),
        )

    def _hide_find_bar(self) -> None:
        bar = getattr(self, "_find_bar", None)
        if bar is None:
            return
        clear_find_highlights(self._current_preview_widget())
        bar.set_not_found(False)
        bar.hide()
        close = getattr(self, "actionFindClose", None)
        if close is not None:
            close.setEnabled(False)
        welcome = getattr(self, "_welcome", None)
        if welcome is not None:
            welcome.hide_lookup()

    def status_text(self) -> str:
        return self.statusBar().currentMessage()

    def show_status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def is_closing(self) -> bool:
        return self._closing

    def focus_path(self) -> str | None:
        page = self._tabs.currentWidget()
        for document in self._documents.values():
            if document.page is page:
                return str(document.path)
        return None

    def _current_document_id(self) -> str | None:
        page = self._tabs.currentWidget()
        for document_id, document in self._documents.items():
            if document.page is page:
                return document_id
        return None

    def _refresh_preview_actions(self, _index: int | None = None) -> None:
        document_id = self._current_document_id()
        document = self._documents.get(document_id) if document_id is not None else None
        office_suffix = (
            document is not None
            and document.path.suffix.lower() in OFFICE_SUFFIXES
        )
        office_enabled = (
            office_suffix
            and document is not None
            and document.office_available is not False
            and document.mode != "office"
            and document.last_result is not None
            and document.availability_request_id is None
        )
        self.actionOfficePreview.setEnabled(office_enabled)
        if (
            office_suffix
            and document is not None
            and document.availability_request_id is not None
        ):
            office_tooltip = "正在检测 Microsoft Office…"
        elif office_suffix and document is not None and document.office_available is None:
            office_tooltip = "点击后检测 Microsoft Office"
        elif office_suffix and document is not None and document.office_available is False:
            office_tooltip = "未检测到 Microsoft Office"
        else:
            office_tooltip = ""
        self.actionOfficePreview.setToolTip(office_tooltip)
        self.actionBuiltinPreview.setEnabled(
            document is not None
            and document.mode != document.builtin_mode
            and document.last_result is not None
        )
        is_pptx = (
            document is not None and document.path.suffix.lower() == ".pptx"
        )
        is_md = (
            document is not None and document.path.suffix.lower() == ".md"
        )
        self.actionTextPreview.setEnabled(
            document is not None
            and document.mode != "text"
            and (
                (is_pptx and document.last_result is not None)
                or is_md
            )
        )
        self.actionVisualPreview.setEnabled(
            document is not None
            and document.mode != "visual"
            and (is_pptx or is_md)
            and (is_md or document.last_result is not None)
        )
        editable = self._editable_view(document) is not None
        self.actionSave.setEnabled(editable)
        self.actionSaveAs.setEnabled(editable)
        self.actionMarkdownEdit.setEnabled(
            is_md and document is not None and document.mode != "text"
        )
        self.actionMarkdownPreview.setEnabled(
            is_md and document is not None and document.mode != "visual"
        )
        self._title_chrome.set_markdown_mode(
            document.mode if is_md and document is not None else None
        )
        self._apply_terminal_passthrough(document)
        self.statusBar().showMessage(document.status_label if document is not None else "")

    def _apply_terminal_passthrough(self, document: _Document | None) -> None:
        # On a terminal tab, Ctrl-letter document shortcuts must reach the shell.
        on_terminal = (
            document is not None
            and document.page.findChild(QWidget, "terminalPage") is not None
        )
        always_on = (
            self.actionOpen,
            self.actionFind,
            self.actionReplace,
            self.actionGoToLine,
            self.actionNewText,
        )
        for action in always_on:
            action.setEnabled(not on_terminal)
        if on_terminal:
            for action in (
                self.actionSave,
                self.actionSaveAs,
                self.actionMarkdownEdit,
                self.actionMarkdownPreview,
            ):
                action.setEnabled(False)

    def _forget_document_for_page(self, page: QWidget | None) -> None:
        if page is None:
            return
        document_id = next(
            (key for key, document in self._documents.items() if document.page is page),
            None,
        )
        if document_id is None:
            return
        document = self._documents.pop(document_id)
        if document.request_id is not None:
            self._requests.pop(document.request_id, None)
            self._owned_request_ids.discard(document.request_id)
            self._executor.cancel(document.request_id)
        self._cancel_availability_probe(document)
        self._dispose_document_content(document)
        _cleanup_dir(document.artifact_dir)
        if document.builtin_artifact_dir != document.artifact_dir:
            _cleanup_dir(document.builtin_artifact_dir)

    def _ask_unsaved_changes(self, name: str) -> str:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Reader")
        box.setText(f"是否将更改保存到 {name}？")
        save = box.addButton("保存", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("不保存", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(save)
        box.exec()
        clicked = box.clickedButton()
        if clicked is save:
            return "save"
        if clicked is discard:
            return "discard"
        return "cancel"

    def _is_dirty(self, document: _Document | None) -> bool:
        view = self._editable_view(document)
        return view is not None and bool(view.dirty)

    def _confirm_discard(self, document_id: str) -> bool:
        document = self._documents.get(document_id)
        if not self._is_dirty(document):
            return True
        assert document is not None
        self._tabs.setCurrentWidget(document.page)
        name = self._editable_view(document).display_title().lstrip("*")
        prompt = self.unsaved_prompt or self._ask_unsaved_changes
        answer = prompt(name)
        if answer == "discard":
            return True
        if answer == "save":
            return self._save_document(document_id)
        return False

    def close_tab(self, index: int) -> None:
        page = self._tabs.widget(index)
        if page is None:
            return
        document_id = next(
            (key for key, document in self._documents.items() if document.page is page),
            None,
        )
        if document_id is not None and not self._confirm_discard(document_id):
            return
        self._forget_document_for_page(page)
        self._tabs.removeTab(index)
        page.deleteLater()
        self._refresh_preview_actions()
        self._refresh_content_stack()

    def _blank_tab_index(self, preferred_page: QWidget | None = None) -> int | None:
        if preferred_page is not None:
            preferred_index = self._tabs.indexOf(preferred_page)
            if (
                preferred_index >= 0
                and preferred_page.property("readerBlankTab") is True
                and not self._page_is_dirty(preferred_page)
            ):
                return preferred_index
            return None
        for index in range(self._tabs.count()):
            page = self._tabs.widget(index)
            if (
                page is not None
                and page.property("readerBlankTab") is True
                and not self._page_is_dirty(page)
            ):
                return index
        return None

    def _page_is_dirty(self, page: QWidget) -> bool:
        return any(
            self._is_dirty(document)
            for document in self._documents.values()
            if document.page is page
        )

    def add_blank_tab(self) -> None:
        self.add_untitled_markdown_tab()

    def _build_new_tab_menu(self) -> None:
        from PySide6.QtWidgets import QMenu

        from reader.shell.icons import line_icon

        menu = QMenu(self)
        self.actionMenuNewFile = QAction(line_icon("new_file"), "新建文件", menu)
        self.actionMenuNewFile.setObjectName("actionMenuNewFile")
        self.actionMenuNewFile.setToolTip("新建 Markdown 文件")
        self.actionMenuNewFile.triggered.connect(self.add_untitled_markdown_tab)
        self.actionMenuOpenFile = QAction(line_icon("open_file"), "打开文件", menu)
        self.actionMenuOpenFile.setObjectName("actionMenuOpenFile")
        self.actionMenuOpenFile.setToolTip("打开电脑上的文件")
        self.actionMenuOpenFile.triggered.connect(self._open_dialog)
        self.actionMenuBrowser = QAction(line_icon("browser"), "Browser", menu)
        self.actionMenuBrowser.setObjectName("actionMenuBrowser")
        self.actionMenuBrowser.setToolTip("在新标签中浏览网页")
        self.actionMenuBrowser.triggered.connect(self.add_browser_tab)
        terminal_menu = QMenu("Terminal", menu)
        terminal_menu.setIcon(line_icon("terminal"))
        self.actionTerminalPowerShell = QAction(line_icon("terminal"), "PowerShell", terminal_menu)
        self.actionTerminalPowerShell.setObjectName("actionTerminalPowerShell")
        self.actionTerminalPowerShell.triggered.connect(
            lambda _checked=False: self.add_terminal_tab("powershell")
        )
        self.actionTerminalCmd = QAction(line_icon("command"), "Command Prompt", terminal_menu)
        self.actionTerminalCmd.setObjectName("actionTerminalCmd")
        self.actionTerminalCmd.triggered.connect(lambda _checked=False: self.add_terminal_tab("cmd"))
        terminal_menu.addAction(self.actionTerminalPowerShell)
        terminal_menu.addAction(self.actionTerminalCmd)
        self.actionMenuTerminal = terminal_menu.menuAction()
        self.actionMenuTerminal.setObjectName("actionMenuTerminal")
        self.actionMenuTerminal.setToolTip("在新标签中打开终端")
        menu.addAction(self.actionMenuNewFile)
        menu.addAction(self.actionMenuOpenFile)
        menu.addSeparator()
        menu.addAction(self.actionMenuBrowser)
        menu.addMenu(terminal_menu)
        self._title_chrome.set_new_menu(menu)

    def add_untitled_markdown_tab(self) -> None:
        from reader.preview.md_text_view import MarkdownTextView

        document_id = uuid4().hex
        path = Path(f"未命名-{document_id[:8]}.md")
        page = QWidget()
        page.setProperty("readerBlankTab", True)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        view = MarkdownTextView(page)
        view.load_untitled()
        layout.addWidget(view)
        document = _Document(
            path=path,
            page=page,
            mode="text",
            builtin_mode="text",
            status_label="文本编辑",
            last_result=PreviewResult(html="", status_label="文本编辑", kind="html"),
        )
        self._documents[document_id] = document
        self._tabs.addTab(page, view.display_title())
        self._tabs.setCurrentWidget(page)
        view.dirty_changed.connect(
            lambda _dirty, did=document_id: self._sync_markdown_tab_title(did)
        )
        view.path_changed.connect(
            lambda _path, did=document_id: self._on_markdown_path_changed(did)
        )
        self._adopt_markdown_editor(document_id, view)
        self._refresh_content_stack()
        self._refresh_preview_actions()

    def _editable_view(self, document: _Document | None) -> QWidget | None:
        from reader.preview.code_view import CodeTextView
        from reader.preview.md_text_view import MarkdownTextView

        if document is None:
            return None
        view = document.page.findChild(MarkdownTextView)
        if view is not None:
            return view
        return document.page.findChild(CodeTextView)

    def _sync_markdown_tab_title(self, document_id: str) -> None:
        document = self._documents.get(document_id)
        view = self._editable_view(document)
        if document is None or view is None:
            return
        index = self._tabs.indexOf(document.page)
        if index >= 0:
            self._tabs.setTabText(index, view.display_title())

    def _on_markdown_path_changed(self, document_id: str) -> None:
        document = self._documents.get(document_id)
        view = self._editable_view(document)
        if document is None or view is None or view.path is None:
            return
        document.path = Path(view.path).resolve()
        document.page.setProperty("readerBlankTab", False)
        remember_recent(document.path)
        if document.md_preview is not None and not self._markdown_preview_matches(
            document, document.md_preview
        ):
            self._discard_kept_preview(document)
            self._schedule_markdown_preview(document_id)
        self._sync_markdown_tab_title(document_id)
        self._refresh_preview_actions()

    def _bind_editable_view(self, document_id: str, view: QWidget) -> None:
        view.dirty_changed.connect(
            lambda _dirty, did=document_id: self._sync_markdown_tab_title(did)
        )
        view.path_changed.connect(
            lambda _path, did=document_id: self._on_markdown_path_changed(did)
        )

    def save_current_tab(self) -> bool:
        document_id = self._current_document_id()
        if document_id is None:
            return False
        return self._save_document(document_id)

    def save_current_tab_as(self) -> bool:
        document_id = self._current_document_id()
        if document_id is None:
            return False
        return self._save_document_as(document_id)

    def _save_document(self, document_id: str) -> bool:
        view = self._editable_view(self._documents.get(document_id))
        if view is None:
            return False
        if view.path is None:
            return self._save_document_as(document_id)
        if not view.save():
            self.statusBar().showMessage("只读文件无法保存")
            return False
        self._sync_markdown_tab_title(document_id)
        self.statusBar().showMessage("已保存")
        return True

    def _save_document_as(self, document_id: str) -> bool:
        from reader.preview.md_text_view import MarkdownTextView

        view = self._editable_view(self._documents.get(document_id))
        if view is None:
            return False
        is_markdown = isinstance(view, MarkdownTextView)
        suffix = ".md" if is_markdown else (view.suffix or ".txt")
        default_name = view.path.name if view.path is not None else f"未命名{suffix}"
        filters = (
            "Markdown (*.md)"
            if is_markdown
            else ";;".join(
                (
                    "文本文件 (*.txt)",
                    "JSON (*.json)",
                    "YAML (*.yaml *.yml)",
                    "XML (*.xml)",
                    "C/C++ (*.c *.h *.cpp *.hpp *.cc *.cxx *.hh *.hxx *.inl *.ipp)",
                    "Markdown (*.md)",
                    "所有文件 (*)",
                )
            )
        )
        path, _selected = QFileDialog.getSaveFileName(self, "另存为", default_name, filters)
        if not path:
            return False
        target = Path(path)
        if is_markdown and target.suffix.lower() != ".md":
            target = target.with_suffix(".md")
        try:
            view.save_as(target)
        except OSError as exc:
            self.statusBar().showMessage(f"保存失败：{exc}")
            return False
        self._on_markdown_path_changed(document_id)
        self.statusBar().showMessage("已保存")
        return True

    def _add_tool_tab(self, content: QWidget, title: str, status: str) -> str:
        document_id = uuid4().hex
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content)
        self._documents[document_id] = _Document(
            path=Path(f"{title}-{document_id[:8]}"),
            page=page,
            mode="builtin",
            builtin_mode="builtin",
            status_label=status,
            last_result=PreviewResult(html="", status_label=status, kind="html"),
        )
        self._tabs.addTab(page, title)
        self._tabs.setCurrentWidget(page)
        self._refresh_content_stack()
        self._refresh_preview_actions()
        return document_id

    def _set_tool_tab_title(self, document_id: str, title: str, fallback: str) -> None:
        document = self._documents.get(document_id)
        if document is None:
            return
        index = self._tabs.indexOf(document.page)
        if index < 0:
            return
        text = title.strip() or fallback
        if len(text) > 32:
            text = text[:31] + "…"
        self._tabs.setTabText(index, text)
        self._tabs.setTabToolTip(index, title)

    def add_browser_tab(self) -> None:
        from reader.shell.browser_page import BrowserPage

        view = BrowserPage()
        document_id = self._add_tool_tab(view, "浏览器", "浏览器")
        view.title_changed.connect(
            lambda title, did=document_id: self._set_tool_tab_title(did, title, "浏览器")
        )
        view.focus_address()

    def _terminal_start_dir(self) -> Path:
        document_id = self._current_document_id()
        document = self._documents.get(document_id) if document_id else None
        if document is not None:
            try:
                if document.path.is_file():
                    return document.path.resolve().parent
            except OSError:
                pass
        return Path.home()

    def add_terminal_tab(self, profile: str = "powershell") -> None:
        from reader.shell.terminal_page import TerminalPage

        view = TerminalPage(profile, self._terminal_start_dir())
        self._add_tool_tab(view, view.title(), view.title())
        view.focus_terminal()

    def add_untitled_text_tab(self) -> None:
        from reader.preview.code_view import CodeTextView

        document_id = uuid4().hex
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        view = CodeTextView(page)
        view.load_untitled(".txt")
        layout.addWidget(view)
        document = _Document(
            path=Path(f"未命名-{document_id[:8]}.txt"),
            page=page,
            mode="builtin",
            builtin_mode="builtin",
            status_label="文本编辑",
            last_result=PreviewResult(html="", status_label="文本编辑", kind="code"),
        )
        self._documents[document_id] = document
        self._tabs.addTab(page, view.display_title())
        self._tabs.setCurrentWidget(page)
        self._bind_editable_view(document_id, view)
        self._refresh_content_stack()
        self._refresh_preview_actions()
        view.editor().setFocus()
    def _open_markdown_text_tab(
        self,
        path: Path,
        *,
        replace_tab_index: int | None = None,
    ) -> None:
        from reader.preview.md_text_view import MarkdownTextView

        document_id = uuid4().hex
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        view = MarkdownTextView(page)
        view.load_path(path, editable=False)
        layout.addWidget(view)
        resolved = path.resolve()
        document = _Document(
            path=resolved,
            page=page,
            mode="text",
            builtin_mode="text",
            status_label="文本编辑",
            last_result=PreviewResult(html="", status_label="文本编辑", kind="html"),
        )
        self._documents[document_id] = document
        if replace_tab_index is None:
            self._tabs.addTab(page, view.display_title())
        else:
            old_page = self._tabs.widget(replace_tab_index)
            self._tabs.removeTab(replace_tab_index)
            self._forget_document_for_page(old_page)
            if old_page is not None:
                old_page.deleteLater()
            self._tabs.insertTab(replace_tab_index, page, view.display_title())
        self._tabs.setCurrentWidget(page)
        view.dirty_changed.connect(
            lambda _dirty, did=document_id: self._sync_markdown_tab_title(did)
        )
        view.path_changed.connect(
            lambda _path, did=document_id: self._on_markdown_path_changed(did)
        )
        self._adopt_markdown_editor(document_id, view)
        self._refresh_content_stack()
        self._refresh_preview_actions()

    def _open_dialog(self) -> None:
        paths, _selected_filter = QFileDialog.getOpenFileNames(
            self,
            "打开",
            "",
            "Documents (*.docx *.pptx *.xlsx *.md *.pdf *.json *.yaml *.yml *.xml *.c *.h *.cpp *.hpp *.cc *.cxx *.hh *.hxx *.inl *.ipp *.txt *.svg *.png *.jpg *.jpeg *.gif *.webp *.bmp *.bin)",
        )
        if paths:
            self.open_paths([str(path) for path in paths])

    def open_paths(
        self,
        paths: list[str],
        *,
        replace_blank: bool = False,
        replace_blank_page: QWidget | None = None,
    ) -> None:
        if self._closing:
            return
        if not self.isVisible():
            self._welcome_allowed = False
            self._opened_files_before_show = True
        existing = [document.path for document in self._documents.values()]
        decision = decide_open(existing, [Path(path) for path in paths])

        if decision.rejected:
            rejected = ", ".join(path.name for path, _reason in decision.rejected)
            self.statusBar().showMessage(f"无法打开：{rejected}")

        blank_index: int | None = None
        if replace_blank_page is not None:
            blank_index = self._blank_tab_index(preferred_page=replace_blank_page)
        elif replace_blank:
            blank_index = self._blank_tab_index()
        for index, path in enumerate(decision.to_open):
            reuse_index = blank_index if index == 0 else None
            self._start_preview(path, replace_tab_index=reuse_index)
            remember_recent(path)
        if decision.to_focus is not None:
            self._focus(decision.to_focus)
            remember_recent(decision.to_focus)
        if self._tabs.count() == 0:
            self._welcome.reload_recent()

    def show_open_path(self, path: Path) -> bool:
        """Make the tab showing ``path`` current; False when this window lacks it."""
        if self._closing:
            return False
        for document in self._documents.values():
            if document.path is not None and document.path == path:
                self._tabs.setCurrentWidget(document.page)
                return True
        return False

    # -- moving tabs between windows ----------------------------------------------

    def _show_tab_menu(self, pos) -> None:
        bar = self._tabs.tabBar()
        index = bar.tabAt(pos)
        if index < 0:
            return
        menu = self._build_tab_menu(index)
        menu.exec(bar.mapToGlobal(pos))
        menu.deleteLater()

    def _build_tab_menu(self, index: int):
        from PySide6.QtWidgets import QMenu

        page = self._tabs.widget(index)
        menu = QMenu(self)
        move = menu.addAction("移到新窗口")
        move.setEnabled(self._tabs.count() > 1 and self._on_new_window is not None)
        move.triggered.connect(
            lambda _checked=False, tab=page: self.move_tab_to_new_window(
                self._tabs.indexOf(tab)
            )
        )
        menu.addSeparator()
        close = menu.addAction("关闭标签")
        close.triggered.connect(
            lambda _checked=False, tab=page: self.close_tab(self._tabs.indexOf(tab))
        )
        return menu

    def _document_id_for_page(self, page: QWidget | None) -> str | None:
        return next(
            (key for key, document in self._documents.items() if document.page is page),
            None,
        )

    def _window_at(self, global_pos: QPoint) -> MainWindow | None:
        widget = QApplication.widgetAt(global_pos)
        window = widget.window() if widget is not None else None
        if isinstance(window, MainWindow) and not window.is_closing():
            return window
        return None

    def _finish_tab_drag(self, index: int, global_pos: QPoint) -> None:
        """Land a tab dragged off the strip: another window, a new window, or here."""
        document_id = self._document_id_for_page(self._tabs.widget(index))
        if document_id is None or self._closing:
            return
        target = self._window_at(global_pos)
        if target is self:
            return
        if target is not None:
            bar = target._tabs.tabBar()
            slot = bar.tabAt(bar.mapFromGlobal(global_pos))
            if self.move_document_to(document_id, target, index=slot if slot >= 0 else None):
                target.raise_()
                target.activateWindow()
            return
        if self._tabs.count() == 1:
            self._place_by_tab(self, global_pos)
            return
        torn = self.move_tab_to_new_window(index)
        if torn is not None:
            self._place_by_tab(torn, global_pos)

    @staticmethod
    def _place_by_tab(window: MainWindow, global_pos: QPoint) -> None:
        if window.isMaximized():
            window.showNormal()
        window.move(global_pos - TEAR_OFF_GRAB)

    def move_tab_to_new_window(self, index: int) -> MainWindow | None:
        document_id = self._document_id_for_page(self._tabs.widget(index))
        if document_id is None or self._on_new_window is None or self._closing:
            return None
        target = self._on_new_window()
        if not self.move_document_to(document_id, target):
            return None
        target.show()
        target.raise_()
        target.activateWindow()
        return target

    def move_document_to(
        self,
        document_id: str,
        target: MainWindow,
        index: int | None = None,
    ) -> bool:
        """Hand a tab, with its live widgets and state, to another window."""
        document = self._documents.get(document_id)
        if (
            document is None
            or target is self
            or self._closing
            or target.is_closing()
        ):
            return False
        tab_index = self._tabs.indexOf(document.page)
        if tab_index < 0:
            return False
        title = self._tabs.tabText(tab_index)
        tooltip = self._tabs.tabToolTip(tab_index)
        icon = self._tabs.tabIcon(tab_index)
        if self._tabs.currentIndex() == tab_index:
            self._hide_find_bar()
            self._hide_goto_bar()
        visual_widget = document.visual_widget
        self._release_document_bindings(document)
        restart_mode = self._hand_over_requests(document, target)

        del self._documents[document_id]
        self._tabs.removeTab(tab_index)
        target._adopt_document(
            document_id,
            document,
            title=title,
            tooltip=tooltip,
            icon=icon,
            index=index,
            visual_widget=visual_widget,
        )
        if restart_mode is not None:
            target._restart_preview(document_id, restart_mode)
        self._refresh_preview_actions()
        self._refresh_content_stack()
        if self._tabs.count() == 0:
            self.close()
        return True

    def _release_document_bindings(self, document: _Document) -> None:
        import sys

        from reader.preview.code_view import CodeTextView
        from reader.preview.md_text_view import MarkdownTextView

        if document.md_push_timer is not None:
            document.md_push_timer.stop()
            document.md_push_timer.deleteLater()
            document.md_push_timer = None
        self._disconnect_visual_events(document)
        browser_module = sys.modules.get("reader.shell.browser_page")
        browser_type = getattr(browser_module, "BrowserPage", None)
        for widget in document.page.findChildren(QWidget):
            if isinstance(widget, (MarkdownTextView, CodeTextView)):
                for signal in (widget.dirty_changed, widget.path_changed):
                    try:
                        signal.disconnect()
                    except (RuntimeError, TypeError):
                        pass
                slot = getattr(widget, "_reader_live_push_slot", None)
                if slot is not None:
                    try:
                        widget._editor.textChanged.disconnect(slot)
                    except (RuntimeError, TypeError):
                        pass
                    del widget._reader_live_push_slot
                    widget.setProperty("readerLivePush", False)
            elif browser_type is not None and isinstance(widget, browser_type):
                try:
                    widget.title_changed.disconnect()
                except (RuntimeError, TypeError):
                    pass

    def _hand_over_requests(self, document: _Document, target: MainWindow):
        """Move in-flight work to ``target``; returns a mode to restart, if any."""
        shared = self._executor is target._executor
        restart_mode = None
        request_id = document.request_id
        request = self._requests.pop(request_id, None) if request_id is not None else None
        if request is not None:
            self._owned_request_ids.discard(request_id)
            if shared:
                target._requests[request_id] = request
                target._owned_request_ids.add(request_id)
            else:
                self._executor.cancel(request_id)
                document.request_id = None
                restart_mode = request[2]
        availability_id = document.availability_request_id
        if availability_id is not None:
            pending = self._availability_requests.pop(availability_id, None)
            if shared and pending is not None:
                target._availability_requests[availability_id] = pending
            else:
                self._executor.cancel(availability_id)
                document.availability_request_id = None
                document.office_requested = False
        return restart_mode

    def _adopt_document(
        self,
        document_id: str,
        document: _Document,
        *,
        title: str,
        tooltip: str,
        icon: QIcon,
        index: int | None,
        visual_widget: QWidget | None,
    ) -> None:
        import sys

        from reader.preview.code_view import CodeTextView
        from reader.preview.md_text_view import MarkdownTextView

        self._documents[document_id] = document
        if index is None or not 0 <= index <= self._tabs.count():
            index = self._tabs.count()
        index = self._tabs.insertTab(index, document.page, icon, title)
        self._tabs.setTabToolTip(index, tooltip)
        browser_module = sys.modules.get("reader.shell.browser_page")
        browser_type = getattr(browser_module, "BrowserPage", None)
        for widget in document.page.findChildren(QWidget):
            if isinstance(widget, (MarkdownTextView, CodeTextView)):
                self._bind_editable_view(document_id, widget)
            elif browser_type is not None and isinstance(widget, browser_type):
                widget.title_changed.connect(
                    lambda text, did=document_id: self._set_tool_tab_title(
                        did, text, "浏览器"
                    )
                )
        editor = self._markdown_editor(document)
        if editor is not None:
            self._adopt_markdown_editor(document_id, editor)
        if visual_widget is not None:
            self._bind_visual_events(document_id, document.generation, visual_widget)
        self._tabs.setCurrentWidget(document.page)
        self._refresh_content_stack()
        self._refresh_preview_actions()

    def _focus(self, path: Path) -> None:
        for document in self._documents.values():
            if document.path == path:
                self._tabs.setCurrentWidget(document.page)
                return

    def _start_preview(self, path: Path, *, replace_tab_index: int | None = None) -> None:
        if self._closing:
            return
        initial_mode: Literal["builtin", "visual"] = (
            "visual"
            if path.suffix.lower() in {".pptx", ".md"}
            else "builtin"
        )
        document_id = uuid4().hex
        page = QWidget()
        layout = QVBoxLayout(page)
        loading = QLabel("正在加载…")
        loading.setObjectName("previewLoading")
        loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading.setStyleSheet(f"color: {MUTED}; background: {PAGE_FILL};")
        layout.addWidget(loading)
        document = _Document(
            path=path,
            page=page,
            request_id=document_id,
            mode=initial_mode,
            builtin_mode=initial_mode,
        )
        self._documents[document_id] = document
        self._requests[document_id] = (
            document_id,
            0,
            initial_mode,
            initial_mode,
            "正在加载…",
        )
        self._owned_request_ids.add(document_id)
        if replace_tab_index is None:
            self._tabs.addTab(page, path.name)
        else:
            old_page = self._tabs.widget(replace_tab_index)
            self._tabs.removeTab(replace_tab_index)
            self._forget_document_for_page(old_page)
            if old_page is not None:
                old_page.deleteLater()
            self._tabs.insertTab(replace_tab_index, page, path.name)
        self._tabs.setCurrentWidget(page)
        self._refresh_content_stack()
        self.statusBar().showMessage("正在加载…")
        self._executor.submit(
            document_id,
            path,
            self._preview_fn,
            self._office,
            self._cache_factory,
            mode=initial_mode,
        )

    def switch_current_tab_to_office(self) -> None:
        document_id = self._current_document_id()
        if document_id is None:
            return
        document = self._documents[document_id]
        if document.mode == "office":
            return
        if (
            document.path.suffix.lower() not in OFFICE_SUFFIXES
            or document.last_result is None
        ):
            self._refresh_preview_actions()
            return
        if document.office_available is None:
            self._request_office_probe(document_id, document)
            return
        if document.office_available is False:
            self._refresh_preview_actions()
            return
        self._restart_preview(document_id, "office")

    def switch_current_tab_to_builtin(self) -> None:
        document_id = self._current_document_id()
        if document_id is None:
            return
        document = self._documents[document_id]
        if document.last_result is None:
            self._restart_preview(document_id, document.builtin_mode)
            return

        self._cancel_availability_probe(document)
        document.generation += 1
        if document.request_id is not None:
            self._requests.pop(document.request_id, None)
            self._owned_request_ids.discard(document.request_id)
            self._executor.cancel(document.request_id)
            document.request_id = None
        try:
            content = self._viewer_factory(document.last_result, document.path)
        except Exception as exc:
            document.status_label = f"预览失败：{document.path.name}（{exc}）"
            self._refresh_preview_actions()
            return

        document.mode = document.builtin_mode
        document.status_label = document.last_result.status_label
        if not self._install_document_content(
            document_id,
            document,
            content,
            document.generation,
        ):
            return
        if document.artifact_dir != document.builtin_artifact_dir:
            _cleanup_dir(document.artifact_dir)
        document.artifact_dir = document.builtin_artifact_dir
        self._refresh_preview_actions()

    def switch_current_tab_to_text(self) -> None:
        document_id = self._current_document_id()
        if document_id is None:
            return
        document = self._documents[document_id]
        suffix = document.path.suffix.lower()
        if document.mode == "text":
            return
        if suffix == ".md":
            self._restore_markdown_text(document_id, document)
            return
        if suffix != ".pptx":
            return
        self._restart_preview(document_id, "text")

    def _on_markdown_mode_requested(self, mode: str) -> None:
        action = self.actionMarkdownEdit if mode == "text" else self.actionMarkdownPreview
        action.trigger()
        self._refresh_preview_actions()

    def _shortcut_markdown_edit(self) -> None:
        document_id = self._current_document_id()
        if document_id is None:
            return
        document = self._documents[document_id]
        if document.path.suffix.lower() != ".md" or document.mode == "text":
            return
        self._restore_markdown_text(document_id, document, editable=True)

    def _shortcut_markdown_preview(self) -> None:
        document_id = self._current_document_id()
        if document_id is None:
            return
        document = self._documents[document_id]
        if document.path.suffix.lower() != ".md" or document.mode == "visual":
            return
        self.switch_current_tab_to_visual()

    def switch_current_tab_to_visual(self) -> None:
        document_id = self._current_document_id()
        if document_id is None:
            return
        document = self._documents[document_id]
        suffix = document.path.suffix.lower()
        if document.mode == "visual":
            return
        if suffix == ".md":
            if not self._show_markdown_preview(document_id, document):
                self._restart_preview(document_id, "visual")
            return
        if suffix != ".pptx":
            return
        self._restart_preview(document_id, "visual")

    def _restore_markdown_text(
        self,
        document_id: str,
        document: _Document,
        *,
        editable: bool = True,
    ) -> None:
        from reader.preview.md_text_view import MarkdownTextView

        self._cancel_availability_probe(document)
        document.generation += 1
        if document.request_id is not None:
            self._requests.pop(document.request_id, None)
            self._owned_request_ids.discard(document.request_id)
            self._executor.cancel(document.request_id)
            document.request_id = None
        self._disconnect_visual_events(document)
        self._keep_current_preview(document)
        view = document.md_editor
        document.md_editor = None
        reused = view is not None
        if view is None:
            view = MarkdownTextView(document.page)
            if document.path.exists():
                view.load_path(document.path, editable=editable)
            else:
                view.load_untitled()
        if not self._install_document_content(
            document_id,
            document,
            view,
            document.generation,
        ):
            return
        view.show()
        if reused and editable:
            view.enable_editing()
        document.mode = "text"
        document.builtin_mode = "text"
        document.status_label = "文本编辑"
        document.last_result = PreviewResult(
            html="", status_label="文本编辑", kind="html"
        )
        if not reused:
            view.dirty_changed.connect(
                lambda _dirty, did=document_id: self._sync_markdown_tab_title(did)
            )
            view.path_changed.connect(
                lambda _path, did=document_id: self._on_markdown_path_changed(did)
            )
        self._adopt_markdown_editor(document_id, view)
        self._sync_markdown_tab_title(document_id)
        self._refresh_preview_actions()

    # -- seamless Markdown edit/preview -------------------------------------------

    def _markdown_preview_source(self, document: _Document) -> Path:
        if document.path.is_absolute():
            return document.path
        # Untitled drafts: an empty scratch folder scopes the offline interceptor.
        return Path(tempfile.gettempdir()) / "reader-untitled" / document.path.name

    def _markdown_preview_matches(self, document: _Document, view: QWidget) -> bool:
        try:
            is_usable = getattr(view, "is_usable", None)
            if callable(is_usable) and not is_usable():
                return False
            source_path = getattr(view, "source_path", None)
            if not callable(source_path):
                return False
            expected = self._markdown_preview_source(document)
            return os.path.normcase(os.path.abspath(source_path())) == os.path.normcase(
                os.path.abspath(expected)
            )
        except (RuntimeError, OSError):
            return False

    def _markdown_editor(self, document: _Document):
        from reader.preview.md_text_view import MarkdownTextView

        try:
            return document.page.findChild(MarkdownTextView)
        except RuntimeError:
            return None

    def _adopt_markdown_editor(self, document_id: str, editor: QWidget) -> None:
        if editor.property("readerLivePush") is not True:
            editor.setProperty("readerLivePush", True)
            slot = lambda did=document_id: self._schedule_markdown_push(did)
            editor._editor.textChanged.connect(slot)
            editor._reader_live_push_slot = slot
        self._schedule_markdown_preview(document_id)

    def _schedule_markdown_push(self, document_id: str) -> None:
        document = self._documents.get(document_id)
        if document is None or document.md_preview is None:
            return
        if document.md_push_timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.setInterval(MARKDOWN_PUSH_DELAY_MS)
            timer.timeout.connect(lambda did=document_id: self._push_markdown_text(did))
            document.md_push_timer = timer
        document.md_push_timer.start()

    def _push_markdown_text(self, document_id: str) -> None:
        document = self._documents.get(document_id)
        if document is None:
            return
        if document.md_push_timer is not None:
            document.md_push_timer.stop()
        editor = self._markdown_editor(document)
        preview = document.md_preview
        setter = getattr(preview, "set_source_text", None)
        if editor is not None and callable(setter):
            setter(editor.text())

    def _schedule_markdown_preview(self, document_id: str) -> None:
        # Context object: the callback is dropped if the window is destroyed first.
        QTimer.singleShot(
            MARKDOWN_PRECREATE_DELAY_MS,
            self,
            lambda did=document_id: self._precreate_markdown_preview(did),
        )

    def _precreate_markdown_preview(self, document_id: str) -> None:
        document = self._documents.get(document_id)
        if (
            document is None
            or self._closing
            or not self.isVisible()
            or document.mode != "text"
            or document.md_preview is not None
        ):
            return
        editor = self._markdown_editor(document)
        if editor is None:
            return
        try:
            preview, result = self._create_markdown_preview(document, editor.text())
        except Exception:
            return
        document.md_preview = preview
        document.md_preview_result = result
        start = getattr(preview, "start", None)
        if callable(start):
            start()

    def _create_markdown_preview(self, document: _Document, text: str):
        from reader.formats.md import to_visual_text

        result = to_visual_text(text)
        preview = self._viewer_factory(result, self._markdown_preview_source(document))
        setter = getattr(preview, "set_source_text", None)
        if callable(setter):
            setter(text)
        preview.setParent(document.page)
        preview.hide()
        return preview, result

    def _keep_current_preview(self, document: _Document) -> None:
        """Take the visible preview out of the layout and keep it for the next switch."""
        try:
            layout = document.page.layout()
        except RuntimeError:
            return
        if layout is None:
            return
        for index in range(layout.count() - 1, -1, -1):
            widget = layout.itemAt(index).widget()
            if widget is None or not callable(getattr(widget, "set_source_text", None)):
                continue
            layout.takeAt(index)
            widget.hide()
            if (
                widget.property("readerPreviewReady") is True
                and self._markdown_preview_matches(document, widget)
                and document.md_preview is None
            ):
                document.md_preview = widget
                if document.last_result is not None and document.last_result.kind == "markdown":
                    document.md_preview_result = document.last_result
            else:
                _dispose_widget(widget)

    def _discard_kept_preview(self, document: _Document) -> None:
        widget, document.md_preview = document.md_preview, None
        document.md_preview_result = None
        if widget is not None:
            try:
                _dispose_widget(widget)
            except RuntimeError:
                pass

    def _show_markdown_preview(self, document_id: str, document: _Document) -> bool:
        editor = self._markdown_editor(document)
        if editor is None or document.mode != "text":
            return False
        text = editor.text()
        preview = document.md_preview
        result = document.md_preview_result
        if preview is not None and not self._markdown_preview_matches(document, preview):
            self._discard_kept_preview(document)
            preview = None
        document.md_preview = None
        document.md_preview_result = None
        if preview is None:
            try:
                preview, result = self._create_markdown_preview(document, text)
            except Exception:
                return False
        else:
            setter = getattr(preview, "set_source_text", None)
            if callable(setter):
                setter(text)
        if document.md_push_timer is not None:
            document.md_push_timer.stop()
        if result is None:
            from reader.formats.md import to_visual_text

            result = to_visual_text(text)
        self._cancel_availability_probe(document)
        document.generation += 1
        if document.request_id is not None:
            self._requests.pop(document.request_id, None)
            self._owned_request_ids.discard(document.request_id)
            self._executor.cancel(document.request_id)
            document.request_id = None
        previous = (document.mode, document.builtin_mode, document.status_label, document.last_result)
        document.mode = "visual"
        document.builtin_mode = "visual"
        document.status_label = result.status_label
        document.last_result = result
        editor.setProperty("readerKeepOnRetire", True)
        document.md_editor = editor
        if not self._install_document_content(document_id, document, preview, document.generation):
            document.mode, document.builtin_mode, document.status_label, document.last_result = previous
            document.md_editor = None
            editor.setProperty("readerKeepOnRetire", False)
            self._refresh_preview_actions()
            return True
        if preview.property("readerPreviewReady") is not False:
            preview.show()
            self._retire_previous_content(preview)
            self._refresh_content_stack()
        self._refresh_preview_actions()
        return True

    def _cancel_availability_probe(self, document: _Document) -> None:
        request_id = document.availability_request_id
        if request_id is None:
            return
        self._availability_requests.pop(request_id, None)
        self._executor.cancel(request_id)
        document.availability_request_id = None
        document.office_requested = False

    def _request_office_probe(
        self,
        document_id: str,
        document: _Document,
    ) -> None:
        if (
            self._closing
            or document.availability_request_id is not None
            or document.office_available is not None
            or self._documents.get(document_id) is not document
        ):
            return
        request_id = f"availability:{document_id}:{document.generation}"
        document.office_requested = True
        document.availability_request_id = request_id
        document.status_label = "正在检测 Microsoft Office…"
        self._availability_requests[request_id] = (
            document_id,
            document.generation,
        )
        self._refresh_preview_actions()
        self._executor.probe_office(
            request_id,
            document.path.suffix.lower(),
            self._office,
        )

    def _restart_preview(self, document_id: str, mode: PreviewMode) -> None:
        document = self._documents[document_id]
        previous_mode = document.mode
        previous_status = document.status_label
        self._cancel_availability_probe(document)
        self._disconnect_visual_events(document)
        document.generation += 1
        if document.request_id is not None:
            self._requests.pop(document.request_id, None)
            self._owned_request_ids.discard(document.request_id)
            self._executor.cancel(document.request_id)
        request_id = f"{document_id}:{document.generation}"
        document.request_id = request_id
        document.mode = mode
        document.status_label = "正在加载…"
        document.visual_slide_count = None
        document.visual_slide_index = None
        self._requests[request_id] = (
            document_id,
            document.generation,
            mode,
            previous_mode,
            previous_status,
        )
        self._owned_request_ids.add(request_id)
        self._refresh_preview_actions()
        self._executor.submit(
            request_id,
            document.path,
            self._preview_fn,
            self._office,
            self._cache_factory,
            mode=mode,
        )

    def _dispose_document_content(self, document: _Document) -> None:
        if document.md_push_timer is not None:
            document.md_push_timer.stop()
        self._discard_kept_preview(document)
        editor, document.md_editor = document.md_editor, None
        if editor is not None:
            try:
                _dispose_widget(editor)
            except RuntimeError:
                pass
        self._disconnect_visual_events(document)
        try:
            layout = document.page.layout()
        except RuntimeError:
            return
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                _dispose_widget(widget)

    def _install_document_content(
        self,
        document_id: str,
        document: _Document,
        content: QWidget,
        generation: int,
    ) -> bool:
        current = self._documents.get(document_id)
        if (
            current is not document
            or document.generation != generation
            or self._closing
            or self._tabs.indexOf(document.page) < 0
        ):
            _dispose_widget(content)
            return False
        layout = document.page.layout()
        if layout is None:
            _dispose_widget(content)
            return False
        self._arm_preview_ready(content)
        layout.addWidget(content)
        # Keep the currently visible content on screen until the new content is
        # ready; otherwise the tab is blank (or falls back to the welcome page).
        keep_until_ready = content.property("readerPreviewReady") is False
        for index in range(layout.count() - 1, -1, -1):
            widget = layout.itemAt(index).widget()
            if widget is None or widget is content:
                continue
            if (
                keep_until_ready
                and widget.objectName() != "previewLoading"
                and widget.property("readerPreviewReady") is not False
            ):
                widget.setProperty("readerRetiring", True)
                set_editable = getattr(widget, "_set_editable", None)
                if callable(set_editable):
                    set_editable(False)
                continue
            layout.takeAt(index)
            _retire_widget(widget)
        self._bind_visual_events(document_id, generation, content)
        if content.objectName() == "codeTextView":
            layout.setContentsMargins(0, 0, 0, 0)
            self._bind_editable_view(document_id, content)
        start = getattr(content, "start", None)
        if callable(start):
            start()
        if (
            self._closing
            or self._documents.get(document_id) is not document
            or document.generation != generation
            or layout.indexOf(content) < 0
        ):
            if document.visual_widget is content:
                self._disconnect_visual_events(document)
            if layout.indexOf(content) >= 0:
                layout.removeWidget(content)
                _dispose_widget(content)
            return False
        self._refresh_content_stack()
        return True

    def _disconnect_visual_events(self, document: _Document) -> None:
        for signal, slot in document.visual_connections:
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass
        document.visual_connections.clear()
        document.visual_widget = None

    def _bind_visual_events(
        self,
        document_id: str,
        generation: int,
        widget: QWidget,
    ) -> None:
        document = self._documents.get(document_id)
        if document is None:
            return
        self._disconnect_visual_events(document)
        failed = getattr(widget, "render_failed", None)
        if failed is not None:
            failed_slot = lambda message: self._visual_render_failed(
                document_id,
                generation,
                widget,
                message,
            )
            failed.connect(failed_slot)
            document.visual_connections.append((failed, failed_slot))
        ready = getattr(widget, "ready", None)
        if ready is not None:
            ready_slot = lambda count: self._visual_ready(
                document_id,
                generation,
                widget,
                count,
            )
            ready.connect(ready_slot)
            document.visual_connections.append((ready, ready_slot))
        changed = getattr(widget, "slide_changed", None)
        if changed is not None:
            changed_slot = lambda index: self._visual_slide_changed(
                document_id,
                generation,
                widget,
                index,
            )
            changed.connect(changed_slot)
            document.visual_connections.append((changed, changed_slot))
        open_path = getattr(widget, "open_path", None)
        if open_path is not None:
            open_path_slot = lambda path: self._visual_open_path(
                document_id,
                generation,
                widget,
                path,
            )
            open_path.connect(open_path_slot)
            document.visual_connections.append((open_path, open_path_slot))
        missing_link = getattr(widget, "missing_link", None)
        if missing_link is not None:
            missing_link_slot = lambda target: self._visual_missing_link(
                document_id,
                generation,
                widget,
                target,
            )
            missing_link.connect(missing_link_slot)
            document.visual_connections.append((missing_link, missing_link_slot))
        if document.visual_connections:
            document.visual_widget = widget

    def _active_visual_document(
        self,
        document_id: str,
        generation: int,
        widget: QWidget,
    ) -> _Document | None:
        document = self._documents.get(document_id)
        layout = document.page.layout() if document is not None else None
        if (
            document is None
            or self._closing
            or document.generation != generation
            or document.mode != "visual"
            or layout is None
            or layout.indexOf(widget) < 0
        ):
            return None
        return document

    def _visual_ready(
        self,
        document_id: str,
        generation: int,
        widget: QWidget,
        count: int,
    ) -> None:
        document = self._active_visual_document(
            document_id,
            generation,
            widget,
        )
        if document is not None:
            document.visual_slide_count = count
            if document.last_result is not None and document.last_result.kind == "pptx":
                append_visual_ready(str(document.path), count)
            if document.last_result is not None and document.last_result.kind == "markdown":
                append_markdown_ready(str(document.path))
            self._mark_preview_ready(widget)

    def _visual_slide_changed(
        self,
        document_id: str,
        generation: int,
        widget: QWidget,
        index: int,
    ) -> None:
        document = self._active_visual_document(
            document_id,
            generation,
            widget,
        )
        if document is not None:
            document.visual_slide_index = index

    def _visual_render_failed(
        self,
        document_id: str,
        generation: int,
        widget: QWidget,
        _message: str,
    ) -> None:
        document = self._active_visual_document(
            document_id,
            generation,
            widget,
        )
        if document is None:
            return
        document.status_label = "内置预览（视觉渲染失败）"
        self._mark_preview_ready(widget)
        self._refresh_preview_actions()

    def _visual_open_path(
        self,
        document_id: str,
        generation: int,
        widget: QWidget,
        path: str,
    ) -> None:
        if self._active_visual_document(document_id, generation, widget) is None:
            return
        self.open_paths([path])

    def _visual_missing_link(
        self,
        document_id: str,
        generation: int,
        widget: QWidget,
        target: str,
    ) -> None:
        document = self._active_visual_document(document_id, generation, widget)
        if document is None:
            return
        document.status_label = f"找不到：{target}"
        self._refresh_preview_actions()

    def _restore_failed_request(
        self,
        document_id: str,
        document: _Document,
        *,
        requested_mode: PreviewMode,
        previous_mode: PreviewMode,
        previous_status: str,
        output: _WorkerOutput | None,
    ) -> bool:
        if document.last_result is None:
            return False
        if output is not None:
            _cleanup_dir(output.artifact_dir)
        document.mode = previous_mode
        document.status_label = (
            "内置预览（Office 导出失败）"
            if requested_mode == "office"
            else previous_status
        )
        if previous_mode == "visual":
            layout = document.page.layout()
            current_widget = (
                layout.itemAt(0).widget()
                if layout is not None and layout.count()
                else None
            )
            if current_widget is not None:
                self._bind_visual_events(
                    document_id,
                    document.generation,
                    current_widget,
                )
        self._refresh_preview_actions()
        return True

    @Slot(str)
    def _preview_completed(self, request_id: str) -> None:
        request = self._requests.pop(request_id, None)
        if request is None:
            if request_id in self._owned_request_ids:
                completion = self._executor.take_completion(request_id)
                if completion is not None:
                    output, _error = completion
                    if output is not None:
                        _cleanup_dir(output.artifact_dir)
                if not self._executor.is_running(request_id):
                    self._owned_request_ids.discard(request_id)
            return
        completion = self._executor.take_completion(request_id)
        if not self._executor.is_running(request_id):
            self._owned_request_ids.discard(request_id)
        (
            document_id,
            generation,
            requested_mode,
            previous_mode,
            previous_status,
        ) = request
        document = self._documents.get(document_id)
        if (
            document is None
            or document.generation != generation
            or document.request_id != request_id
        ):
            if completion is not None:
                output, _error = completion
                if output is not None:
                    _cleanup_dir(output.artifact_dir)
            return

        page_is_valid = self._tabs.indexOf(document.page) >= 0
        if self._closing or not page_is_valid:
            if completion is not None:
                output, _error = completion
                if output is not None:
                    _cleanup_dir(output.artifact_dir)
            return

        if completion is None:
            return
        output, error = completion
        document.request_id = None

        office_failed = requested_mode == "office" and (
            error is not None
            or output is None
            or output.result.kind == "error"
        )
        if office_failed and self._restore_failed_request(
            document_id,
            document,
            requested_mode=requested_mode,
            previous_mode=previous_mode,
            previous_status=previous_status,
            output=output,
        ):
            return

        if error is not None:
            if self._restore_failed_request(
                document_id,
                document,
                requested_mode=requested_mode,
                previous_mode=previous_mode,
                previous_status=previous_status,
                output=output,
            ):
                return
            content: QWidget = QLabel(str(error))
            content.setObjectName("previewContent")
            status = f"预览失败：{document.path.name}"
        elif output is None:
            if self._restore_failed_request(
                document_id,
                document,
                requested_mode=requested_mode,
                previous_mode=previous_mode,
                previous_status=previous_status,
                output=output,
            ):
                return
            content = QLabel("未返回预览结果")
            content.setObjectName("previewContent")
            status = f"预览失败：{document.path.name}"
        else:
            result = output.result
            if result.kind == "error":
                if self._restore_failed_request(
                    document_id,
                    document,
                    requested_mode=requested_mode,
                    previous_mode=previous_mode,
                    previous_status=previous_status,
                    output=output,
                ):
                    return
                content = QLabel(result.error or "error")
                content.setObjectName("previewContent")
                status = result.status_label
            else:
                try:
                    content = self._viewer_factory(result, document.path)
                    status = result.status_label
                except Exception as exc:
                    if self._restore_failed_request(
                        document_id,
                        document,
                        requested_mode=requested_mode,
                        previous_mode=previous_mode,
                        previous_status=previous_status,
                        output=output,
                    ):
                        return
                    _cleanup_dir(output.artifact_dir)
                    content = QLabel(str(exc))
                    content.setObjectName("previewContent")
                    status = f"预览失败：{document.path.name}"
                    output = None

        previous_last_result = document.last_result
        previous_builtin_mode = document.builtin_mode
        document.mode = requested_mode
        document.status_label = status
        if output is not None and requested_mode != "office":
            document.last_result = output.result
            document.builtin_mode = requested_mode
        if not self._install_document_content(
            document_id,
            document,
            content,
            generation,
        ):
            document.mode = previous_mode
            document.status_label = previous_status
            document.last_result = previous_last_result
            document.builtin_mode = previous_builtin_mode
            if output is not None:
                _cleanup_dir(output.artifact_dir)
            return

        if output is not None and output.result.kind == "code":
            append_document_ready(
                str(document.path),
                output.result.kind,
                status,
            )

        if output is not None:
            if (
                requested_mode != "office"
                or document.artifact_dir != document.builtin_artifact_dir
            ):
                _cleanup_dir(document.artifact_dir)
            document.artifact_dir = output.artifact_dir
            if requested_mode != "office":
                document.builtin_artifact_dir = output.artifact_dir
        self._refresh_preview_actions()

    @Slot(str, object)
    def _office_availability_completed(
        self,
        request_id: str,
        available: bool,
    ) -> None:
        request = self._availability_requests.pop(request_id, None)
        if request is None:
            return
        document_id, generation = request
        document = self._documents.get(document_id)
        if (
            document is None
            or document.generation != generation
            or document.availability_request_id != request_id
        ):
            return
        document.availability_request_id = None
        document.office_available = bool(available)
        office_requested = document.office_requested
        document.office_requested = False
        if not available:
            document.status_label = "未检测到 Microsoft Office"
        self._refresh_preview_actions()
        if available and office_requested:
            self._restart_preview(document_id, "office")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._closing:
            super().closeEvent(event)
            return
        for document_id in list(self._documents):
            if not self._confirm_discard(document_id):
                event.ignore()
                return
        self._closing = True
        if self._on_closing is not None:
            self._on_closing(self)
        for document_id, document in list(self._documents.items()):
            if document.request_id is not None:
                self._requests.pop(document.request_id, None)
                self._owned_request_ids.discard(document.request_id)
                self._executor.cancel(document.request_id)
            self._cancel_availability_probe(document)
            try:
                self._dispose_document_content(document)
            except RuntimeError:
                pass
            _cleanup_dir(document.artifact_dir)
            if document.builtin_artifact_dir != document.artifact_dir:
                _cleanup_dir(document.builtin_artifact_dir)
        self._documents.clear()
        try:
            self._executor.completed.disconnect(self._preview_completed)
        except (RuntimeError, TypeError):
            pass
        try:
            self._executor.availability_completed.disconnect(
                self._office_availability_completed
            )
        except (RuntimeError, TypeError):
            pass
        if self._owns_executor:
            self._executor.release_when_idle()
        super().closeEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            current = self._tabs.currentWidget()
            self.open_paths(
                paths,
                replace_blank_page=current
                if current is not None and current.property("readerBlankTab") is True
                else None,
            )
            event.acceptProposedAction()


def _window_icon_path() -> Path:
    return resource_path("assets", "icons", "reader.ico")


def _load_icon_if_exists(icon_path: Path, icon_applier: Callable[[QIcon], None]) -> bool:
    if not icon_path.exists():
        return False
    icon_applier(QIcon(str(icon_path)))
    return True


def _send_message_w(hwnd: int, msg: int, wparam: int, lparam: int) -> int:
    prototype = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t,
        wintypes.HWND,
        wintypes.UINT,
        ctypes.c_size_t,
        ctypes.c_ssize_t,
    )
    return int(prototype(("SendMessageW", ctypes.windll.user32))(hwnd, msg, wparam, lparam))


def _load_native_icon(icon_path: Path, cx: int, cy: int) -> int:
    prototype = ctypes.WINFUNCTYPE(
        ctypes.c_void_p,
        wintypes.HINSTANCE,
        wintypes.LPCWSTR,
        wintypes.UINT,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    )
    handle = prototype(("LoadImageW", ctypes.windll.user32))(
        None,
        str(icon_path),
        IMAGE_ICON,
        cx,
        cy,
        LR_LOADFROMFILE,
    )
    return int(handle) if handle else 0
