from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from reader.open import decide_open
from reader.preview.cache import PreviewCache
from reader.preview.office import Win32OfficeBackend
from reader.preview.pipeline import preview
from reader.preview.result import PreviewResult

PreviewFunction = Callable[..., PreviewResult]
CacheFactory = Callable[[], PreviewCache]
ViewerFactory = Callable[[PreviewResult, Path], QWidget]


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


def _pin_pdf(result: PreviewResult) -> _WorkerOutput:
    if result.kind != "pdf" or result.pdf_path is None:
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


class _PreviewWorker(QRunnable):
    def __init__(
        self,
        document_id: str,
        path: Path,
        preview_fn: PreviewFunction,
        office: Win32OfficeBackend,
        cache_factory: CacheFactory,
        signals: _WorkerSignals,
    ) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self.document_id = document_id
        self.path = path
        self.preview_fn = preview_fn
        self.office = office
        self.cache_factory = cache_factory
        self.signals = signals

    @Slot()
    def run(self) -> None:
        result: PreviewResult | None = None
        try:
            cache: PreviewCache | None
            try:
                cache = self.cache_factory()
                result = cache.get(self.path, "auto")
            except Exception:
                cache = None

            if result is None:
                result = self.preview_fn(self.path, office=self.office)
                if cache is not None:
                    try:
                        cache.put(self.path, "auto", result)
                    except Exception:
                        pass
            output = _pin_pdf(result)
        except Exception as exc:
            self.signals.completed.emit(self.document_id, None, exc)
            return
        self.signals.completed.emit(self.document_id, output, None)


class PreviewExecutor(QObject):
    completed = Signal(str)

    def __init__(
        self,
        *,
        thread_pool: QThreadPool | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.thread_pool = thread_pool or QThreadPool(self)
        self.thread_pool.setMaxThreadCount(1)
        self._workers: dict[str, _PreviewWorker] = {}
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
    ) -> None:
        signals = _WorkerSignals(self)
        worker = _PreviewWorker(
            document_id,
            path,
            preview_fn,
            office,
            cache_factory,
            signals,
        )
        signals.completed.connect(
            self._worker_completed,
            Qt.ConnectionType.QueuedConnection,
        )
        self._workers[document_id] = worker
        self.thread_pool.start(worker)

    def cancel(self, document_id: str) -> None:
        if document_id in self._workers:
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
        return len(self._workers) + len(self._pending)

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


@dataclass
class _Document:
    path: Path
    page: QWidget
    artifact_dir: Path | None = None


def _directory_url(path: Path) -> QUrl:
    return QUrl.fromLocalFile(str(path.resolve()) + os.sep)


def _html_base_url(result: PreviewResult, source_path: Path) -> QUrl:
    return _directory_url(result.asset_dir or source_path.parent)


def _default_viewer(result: PreviewResult, source_path: Path) -> QWidget:
    from PySide6.QtWebEngineWidgets import QWebEngineView

    web = QWebEngineView()
    if result.kind == "pdf" and result.pdf_path is not None:
        web.load(QUrl.fromLocalFile(str(result.pdf_path)))
    else:
        web.setHtml(result.html, _html_base_url(result, source_path))
    return web


class MainWindow(QMainWindow):
    def __init__(
        self,
        on_new_window: Callable[[], MainWindow] | None = None,
        *,
        preview_fn: PreviewFunction = preview,
        cache_factory: CacheFactory = PreviewCache,
        viewer_factory: ViewerFactory | None = None,
        executor: PreviewExecutor | None = None,
        thread_pool: QThreadPool | None = None,
        office: Win32OfficeBackend | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Reader")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setAcceptDrops(True)

        self._on_new_window = on_new_window
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
        self._documents: dict[str, _Document] = {}
        self._closing = False

        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self._tabs)
        self.setStatusBar(QStatusBar())

        self.actionNewWindow = QAction("新建窗口", self)
        self.actionNewWindow.setObjectName("actionNewWindow")
        self.actionNewWindow.triggered.connect(self._spawn)
        self.menuBar().addMenu("文件").addAction(self.actionNewWindow)

    def _spawn(self) -> None:
        if self._on_new_window is not None:
            self._on_new_window()

    def tab_count(self) -> int:
        return self._tabs.count()

    def tab_title(self, index: int) -> str:
        return self._tabs.tabText(index)

    def status_text(self) -> str:
        return self.statusBar().currentMessage()

    def focus_path(self) -> str | None:
        page = self._tabs.currentWidget()
        for document in self._documents.values():
            if document.page is page:
                return str(document.path)
        return None

    def close_tab(self, index: int) -> None:
        page = self._tabs.widget(index)
        if page is None:
            return
        document_id = next(
            (key for key, document in self._documents.items() if document.page is page),
            None,
        )
        if document_id is not None:
            document = self._documents.pop(document_id)
            self._executor.cancel(document_id)
            _cleanup_dir(document.artifact_dir)
        self._tabs.removeTab(index)
        page.deleteLater()

    def open_paths(self, paths: list[str]) -> None:
        existing = [document.path for document in self._documents.values()]
        decision = decide_open(existing, [Path(path) for path in paths])

        if decision.rejected:
            rejected = ", ".join(path.name for path, _reason in decision.rejected)
            self.statusBar().showMessage(f"无法打开：{rejected}")

        if decision.to_focus is not None:
            self._focus(decision.to_focus)

        for path in decision.to_open:
            self._start_preview(path)

    def _focus(self, path: Path) -> None:
        for document in self._documents.values():
            if document.path == path:
                self._tabs.setCurrentWidget(document.page)
                return

    def _start_preview(self, path: Path) -> None:
        document_id = uuid4().hex
        page = QWidget()
        layout = QVBoxLayout(page)
        loading = QLabel("正在加载…")
        loading.setObjectName("previewLoading")
        loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(loading)
        self._documents[document_id] = _Document(path=path, page=page)
        self._tabs.addTab(page, path.name)
        self._tabs.setCurrentWidget(page)
        self.statusBar().showMessage("正在加载…")
        self._executor.submit(
            document_id,
            path,
            self._preview_fn,
            self._office,
            self._cache_factory,
        )

    @Slot(str)
    def _preview_completed(self, document_id: str) -> None:
        document = self._documents.get(document_id)
        if document is None:
            return

        page_is_valid = self._tabs.indexOf(document.page) >= 0
        if self._closing or not page_is_valid:
            completion = self._executor.take_completion(document_id)
            if completion is not None:
                output, _error = completion
                if output is not None:
                    _cleanup_dir(output.artifact_dir)
            return

        completion = self._executor.take_completion(document_id)
        if completion is None:
            return
        output, error = completion

        if error is not None:
            content: QWidget = QLabel(str(error))
            content.setObjectName("previewContent")
            status = f"预览失败：{document.path.name}"
        elif output is None:
            content = QLabel("未返回预览结果")
            content.setObjectName("previewContent")
            status = f"预览失败：{document.path.name}"
        else:
            result = output.result
            if result.kind == "error":
                content = QLabel(result.error or "error")
                content.setObjectName("previewContent")
                status = result.status_label
            else:
                try:
                    content = self._viewer_factory(result, document.path)
                    status = result.status_label
                except Exception as exc:
                    _cleanup_dir(output.artifact_dir)
                    content = QLabel(str(exc))
                    content.setObjectName("previewContent")
                    status = f"预览失败：{document.path.name}"
                    output = None

        current = self._documents.get(document_id)
        if current is None or current.page is not document.page or self._closing:
            content.deleteLater()
            if output is not None:
                _cleanup_dir(output.artifact_dir)
            return

        layout = document.page.layout()
        if layout is None:
            content.deleteLater()
            if output is not None:
                _cleanup_dir(output.artifact_dir)
            return
        while layout.count():
            item = layout.takeAt(0)
            old_widget = item.widget()
            if old_widget is not None:
                old_widget.deleteLater()
        layout.addWidget(content)
        if output is not None:
            document.artifact_dir = output.artifact_dir
        self.statusBar().showMessage(status)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._closing = True
        for document_id, document in list(self._documents.items()):
            self._executor.cancel(document_id)
            _cleanup_dir(document.artifact_dir)
        self._documents.clear()
        try:
            self._executor.completed.disconnect(self._preview_completed)
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
            self.open_paths(paths)
            event.acceptProposedAction()
