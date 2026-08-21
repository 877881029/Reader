from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QLabel, QMainWindow, QStatusBar, QTabWidget, QVBoxLayout, QWidget

from reader.open import decide_open
from reader.preview.cache import PreviewCache
from reader.preview.office import Win32OfficeBackend
from reader.preview.pipeline import preview
from reader.preview.result import PreviewResult

PreviewFunction = Callable[..., PreviewResult]
CacheFactory = Callable[[], PreviewCache]
ViewerFactory = Callable[[PreviewResult], QWidget]


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
    ) -> None:
        super().__init__()
        self.document_id = document_id
        self.path = path
        self.preview_fn = preview_fn
        self.office = office
        self.cache_factory = cache_factory
        self.signals = _WorkerSignals()

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
        except Exception as exc:
            self.signals.completed.emit(self.document_id, None, exc)
            return
        self.signals.completed.emit(self.document_id, result, None)


@dataclass
class _Document:
    path: Path
    page: QWidget


def _default_viewer(result: PreviewResult) -> QWidget:
    from PySide6.QtWebEngineWidgets import QWebEngineView

    web = QWebEngineView()
    if result.kind == "pdf" and result.pdf_path is not None:
        web.load(QUrl.fromLocalFile(str(result.pdf_path)))
    else:
        web.setHtml(result.html)
    return web


class MainWindow(QMainWindow):
    def __init__(
        self,
        on_new_window: Callable[[], MainWindow] | None = None,
        *,
        preview_fn: PreviewFunction = preview,
        cache_factory: CacheFactory = PreviewCache,
        viewer_factory: ViewerFactory | None = None,
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
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._office = office or Win32OfficeBackend()
        self._documents: dict[str, _Document] = {}

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
            del self._documents[document_id]
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

        worker = _PreviewWorker(
            document_id,
            path,
            self._preview_fn,
            self._office,
            self._cache_factory,
        )
        worker.signals.completed.connect(self._preview_completed)
        self._thread_pool.start(worker)

    @Slot(str, object, object)
    def _preview_completed(
        self,
        document_id: str,
        result: PreviewResult | None,
        error: Exception | None,
    ) -> None:
        document = self._documents.get(document_id)
        if document is None:
            return

        if error is not None:
            content: QWidget = QLabel(str(error))
            content.setObjectName("previewContent")
            status = f"预览失败：{document.path.name}"
        else:
            assert result is not None
            try:
                content = self._viewer_factory(result)
                status = result.status_label
            except Exception as exc:
                content = QLabel(str(exc))
                content.setObjectName("previewContent")
                status = f"预览失败：{document.path.name}"

        layout = document.page.layout()
        assert layout is not None
        while layout.count():
            item = layout.takeAt(0)
            old_widget = item.widget()
            if old_widget is not None:
                old_widget.deleteLater()
        layout.addWidget(content)
        self.statusBar().showMessage(status)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.open_paths(paths)
            event.acceptProposedAction()
