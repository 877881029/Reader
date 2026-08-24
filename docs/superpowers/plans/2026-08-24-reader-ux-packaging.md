# Reader UX, Icon, and Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix Reader daily-use UX friction and package it as `dist/Reader/Reader.exe` with transparent R icon assets, builtin-first Office preview, file-tab workflows, shell registration, and PyInstaller onedir support.

**Architecture:** Keep the current single Python process, Qt `ReaderApp`, shared serial `PreviewExecutor`, and `MainWindow` tab model. Add small, reviewable interfaces for tab opening/replacement, preview strategy selection, icon asset generation, frozen-vs-development launch target selection, and PyInstaller configuration without restructuring the existing app.

**Tech Stack:** Python 3.12+, PySide6 Qt Widgets/WebEngine, pywin32, python-docx, python-pptx, openpyxl, markdown-it-py, Pillow for deterministic PNG/ICO generation, PyInstaller onedir, pytest, pytest-qt, pytest-mock.

## Global Constraints

- First window is large enough to read (1200×800, centered).
- Multiple files open as tabs; a Notepad-style **+** adds a blank tab; drag-drop and Open add more tabs.
- Office documents default to **fast builtin preview**; user can switch a tab to **Office 高保真** when needed.
- Brand icon is a distinctive blue rounded-ribbon uppercase **R** with transparency inside letter counters and outside the glyph.
- Users launch **Reader.exe**, not `reader.cmd`. Explorer “Open with” and the desktop shortcut target that exe and show the R icon.
- This increment does not add dual pane, translation, or format conversion.
- Do not change system default apps (`UserChoice`).
- PyInstaller onedir vs onefile debate beyond: use **one-folder** (`onedir`) for faster startup and WebEngine compatibility
- macOS / Linux packaging
- Remembering last window size (user chose fixed 1200×800)
- Auto Office-first preview (user chose builtin-first)
- Default geometry: **1200×800**, centered on the primary screen. Minimum size 800×500 so it cannot collapse to a tiny chrome-only window.
- Tab bar (right side): **+** creates a blank tab titled `未命名`. Blank tab shows a drop hint: “拖入文件，或使用 文件 → 打开”.
- **文件 → 打开** (Ctrl+O): native multi-select dialog filtered to `.docx .pptx .xlsx .md`. Each chosen file becomes a new tab.
- Drag onto window, tab bar, or a blank tab: supported files append as new tabs. Dropping onto a **blank** tab replaces that blank tab with the first file; extra files still add new tabs.
- Same resolved path already open in this window: focus existing tab, do not duplicate.
- Last tab close: window stays empty (blank state, no tabs, or one leftover blank — pick **no leftover blank**: empty drop area until + or Open or drop).
- Running instance: second launch / Open with forwards paths via existing single-instance IPC into the **active** window as new tabs. Multiple files in one argv list → multiple tabs.
- **新建窗口** remains; new window also 1200×800 centered with offset (+32,+32) if it would fully overlap.
- Default `preview(path)` for `.docx`/`.pptx`/`.xlsx` uses **builtin HTML only** (do not call Office COM on open). Markdown stays builtin.
- Status: `内置预览`
- Button/menu: **Office 高保真** — enabled only if Office COM is available for that suffix; otherwise disabled with tooltip “未检测到 Microsoft Office”.
- Runs existing COM export on the worker thread.
- On success: status `Office 预览`, replace viewer with PDF/HTML result.
- On failure: keep builtin content, status `内置预览（Office 导出失败）`.
- User can switch back to builtin without re-opening the file.
- Window must appear immediately; tabs show `正在加载…` until builtin HTML is ready. Do not block GUI on COM.
- Serial preview executor stays (COM is not thread-safe); builtin jobs may still share that pool in this increment to avoid a second architecture change.
- Source: concept **C** — rounded-ribbon blue uppercase **R**.
- Only the blue **R** strokes occupy pixels.
- Interior counters of R and the field around R are **fully transparent** (alpha 0), not a white/gray plate, not a filled circle.
- No shortcut overlay in the source asset (Windows may add one on `.lnk`).
- Master: `assets/icons/reader-r.svg` (vector). Raster: PNG 16/24/32/48/256 plus `assets/icons/reader.ico` (multi-size).
- Applied to: `Reader.exe` (version resource), `QApplication`/`MainWindow` window icon, desktop `.lnk` IconLocation, ProgID DefaultIcon.
- Color: saturated blue in the **C** family (approx `#2563EB`), readable on light and dark taskbars.
- Ship a **PyInstaller onedir** build:
- Output: `dist/Reader/Reader.exe` plus `_internal` (or PyInstaller default).
- `--windowed` (no console).
- `--icon assets/icons/reader.ico`.
- Include PySide6 WebEngine resources.
- Version info: ProductName `Reader`, FileDescription `Reader`.
- `register_open_with` and `create_desktop_shortcut` take the **exe path**:
- Command: `"<exe>" "%1"` (Explorer passes one path per invocation; multi-select becomes multiple launches that IPC coalesces, or one launch with multiple `%1` depending on Windows — handle **all argv files**).
- Shortcut Target: `Reader.exe`; WorkingDirectory: exe directory; IconLocation: exe.
- Do not register `scripts/reader.cmd` once the frozen exe exists.
- Development still supports `python -m reader`; first-run association uses `sys.executable` + `-m reader` only when not frozen. Frozen path always uses `sys.executable` as the exe.
- Provide `scripts/build_windows.ps1` that: create venv-or-use current, `pip install -e ".[dev]" pyinstaller`, run PyInstaller spec, copy icon.
- Unsupported drop/open: status message, no new content tab (blank tab stays if user dropped nothing valid).
- Association/shortcut write failure: app still runs; non-blocking status or first-run hint.
- High-fidelity failure: builtin remains visible.
- Missing icon file in dev: Qt default icon, tests still pass with a generated fixture ico if needed.

---

## File Structure

- Create: `assets/icons/reader-r.svg` — reviewable vector source for the transparent blue rounded-ribbon R.
- Create: `assets/icons/reader-16.png` — generated transparent PNG.
- Create: `assets/icons/reader-24.png` — generated transparent PNG.
- Create: `assets/icons/reader-32.png` — generated transparent PNG.
- Create: `assets/icons/reader-48.png` — generated transparent PNG.
- Create: `assets/icons/reader-256.png` — generated transparent PNG.
- Create: `assets/icons/reader.ico` — generated multi-size ICO.
- Create: `scripts/generate_icons.py` — deterministic Pillow icon generator.
- Create: `reader.spec` — PyInstaller onedir spec with WebEngine collection and icon/version resources.
- Create: `scripts/build_windows.ps1` — Windows build script for editable install plus PyInstaller.
- Create: `version_info.txt` — PyInstaller version resource with ProductName `Reader` and FileDescription `Reader`.
- Create: `tests/test_icon_assets.py` — alpha and asset existence tests.
- Create: `tests/test_packaging.py` — static checks for PyInstaller spec and build script.
- Create: `tests/test_main_launch.py` — frozen and development launch target tests.
- Modify: `pyproject.toml` — add `Pillow` to dev dependencies for icon generation/tests.
- Modify: `src/reader/shell/window.py` — geometry, centering, window icon, blank tab, Open dialog, drop replacement, high-fidelity controls.
- Modify: `src/reader/app.py` — centered/offset new-window placement and QApplication icon setup.
- Modify: `src/reader/preview/pipeline.py` — explicit `mode: PreviewMode = "builtin"` interface.
- Modify: `src/reader/__main__.py` — frozen exe launch target, development `python -m reader` association command, app icon setup entry.
- Modify: `src/reader/shell/associate.py` — shortcut `IconLocation`, ProgID `DefaultIcon`, and executable command quoting.
- Modify: `src/reader/ipc.py` — rapid sequential multi-launch forwarding reliability.
- Modify: `tests/test_window.py` — UX, geometry, Open, blank tab, high-fidelity, and regression coverage.
- Modify: `tests/test_pipeline.py` — builtin-first and explicit Office mode coverage.
- Modify: `tests/test_associate.py` — DefaultIcon and shortcut icon coverage.
- Modify: `tests/test_ipc.py` — rapid sequential sends coverage.

---

### Task 1: Window Geometry and Application Icon

**Files:**
- Modify: `src/reader/app.py`
- Modify: `src/reader/shell/window.py`
- Modify: `tests/test_window.py`

**Interfaces:**
- Consumes: existing `ReaderApp.new_window() -> MainWindow`, `MainWindow.__init__(...)`.
- Produces: `MainWindow.DEFAULT_SIZE: tuple[int, int] = (1200, 800)`, `MainWindow.MINIMUM_SIZE: tuple[int, int] = (800, 500)`, `def MainWindow.center_on_screen(offset: int = 0) -> None`, `def ReaderApp._place_window(window: MainWindow) -> None`.

- [ ] **Step 1: Write failing geometry tests**

```python
# tests/test_window.py
def test_main_window_default_size_and_minimum(qtbot):
    from reader.shell.window import MainWindow

    window = MainWindow(viewer_factory=label_viewer)
    qtbot.addWidget(window)

    assert window.size().width() == 1200
    assert window.size().height() == 800
    assert window.minimumSize().width() == 800
    assert window.minimumSize().height() == 500


def test_new_window_offsets_from_existing_window(reader_app):
    app, _ipc = reader_app
    first = app.new_window()
    second = app.new_window()

    assert second.geometry().topLeft() == first.geometry().topLeft() + first.geometry().topLeft().__class__(32, 32)
```

- [ ] **Step 2: Run RED command**

Run: `pytest tests/test_window.py::test_main_window_default_size_and_minimum tests/test_window.py::test_new_window_offsets_from_existing_window -v`

Expected: FAIL because `MainWindow` has no fixed default/minimum size and `ReaderApp.new_window()` does not offset the second window.

- [ ] **Step 3: Add minimal geometry implementation**

```python
# src/reader/shell/window.py
from PySide6.QtCore import QPoint
from PySide6.QtGui import QAction, QCloseEvent, QDragEnterEvent, QDropEvent, QIcon

class MainWindow(QMainWindow):
    DEFAULT_SIZE = (1200, 800)
    MINIMUM_SIZE = (800, 500)

    def __init__(self, on_new_window=None, *, preview_fn=preview, cache_factory=PreviewCache, viewer_factory=None, executor=None, thread_pool=None, office=None) -> None:
        super().__init__()
        self.setWindowTitle("Reader")
        self.resize(*self.DEFAULT_SIZE)
        self.setMinimumSize(*self.MINIMUM_SIZE)
        icon_path = Path(__file__).resolve().parents[3] / "assets" / "icons" / "reader.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setAcceptDrops(True)
        # keep the existing initialization that wires preview, executor, tabs, status bar, and actions

    def center_on_screen(self, offset: int = 0) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        frame.moveTopLeft(frame.topLeft() + QPoint(offset, offset))
        self.move(frame.topLeft())
```

```python
# src/reader/app.py
from pathlib import Path
from PySide6.QtGui import QIcon

def _reader_icon_path() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "icons" / "reader.ico"

class ReaderApp:
    def __init__(self, qapp: QApplication, *, ipc: SingleInstance | None = None) -> None:
        self._qapp = qapp
        icon_path = _reader_icon_path()
        if icon_path.exists():
            self._qapp.setWindowIcon(QIcon(str(icon_path)))
        self._windows: list[MainWindow] = []
        self._executor = PreviewExecutor(parent=qapp)
        self._ipc = ipc if ipc is not None else SingleInstance()
        self._is_primary = self._ipc.become_server(self._on_ipc_paths)
        self._ipc_closed = False

    def new_window(self) -> MainWindow:
        window = MainWindow(on_new_window=self.new_window, executor=self._executor)
        window_id = id(window)
        window.destroyed.connect(lambda *_args, target_id=window_id: self._drop(target_id))
        self._windows.append(window)
        self._place_window(window)
        window.show()
        return window

    def _place_window(self, window: MainWindow) -> None:
        offset = 32 if len(self._windows) > 1 else 0
        window.center_on_screen(offset)
```

- [ ] **Step 4: Run GREEN command**

Run: `pytest tests/test_window.py::test_main_window_default_size_and_minimum tests/test_window.py::test_new_window_offsets_from_existing_window -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/reader/app.py src/reader/shell/window.py tests/test_window.py
git commit -m "feat: set reader window size and icon"
```

---

### Task 2: Blank Tabs, Open Dialog, and Drop Replacement

**Files:**
- Modify: `src/reader/shell/window.py`
- Modify: `tests/test_window.py`

**Interfaces:**
- Consumes: `MainWindow.open_paths(paths: list[str]) -> None`, `decide_open(existing: list[Path], incoming: list[Path]) -> OpenDecision`.
- Produces: `def MainWindow.add_blank_tab() -> None`, `def MainWindow.open_paths(paths: list[str], *, replace_blank: bool = False) -> None`, `def MainWindow._open_dialog() -> None`, `def MainWindow._blank_tab_index() -> int | None`.

- [ ] **Step 1: Write failing blank and Open tests**

```python
# tests/test_window.py
def test_plus_action_adds_blank_tab_with_drop_hint(qtbot):
    window = make_window(lambda _path, office=None: builtin_result())
    qtbot.addWidget(window)

    window.actionNewTab.trigger()

    assert window.tab_count() == 1
    assert window.tab_title(0) == "未命名"
    assert "拖入文件，或使用 文件 → 打开" in page_text(window, 0)
    assert window.focus_path() is None


def test_open_action_uses_multi_select_and_adds_tabs(qtbot, tmp_path: Path, monkeypatch):
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("1", encoding="utf-8")
    second.write_text("2", encoding="utf-8")
    window = make_window(lambda path, office=None: builtin_result(path.name))
    qtbot.addWidget(window)
    monkeypatch.setattr(
        "reader.shell.window.QFileDialog.getOpenFileNames",
        lambda *_args, **_kwargs: ([str(first), str(second)], "Documents"),
    )

    window.actionOpen.trigger()

    assert window.tab_count() == 2
    assert window.tab_title(0) == "first.md"
    assert window.tab_title(1) == "second.md"
```

- [ ] **Step 2: Run RED command**

Run: `pytest tests/test_window.py::test_plus_action_adds_blank_tab_with_drop_hint tests/test_window.py::test_open_action_uses_multi_select_and_adds_tabs -v`

Expected: FAIL because `actionNewTab`, `actionOpen`, blank tab creation, and dialog injection do not exist.

- [ ] **Step 3: Add minimal blank tab and Open implementation**

```python
# src/reader/shell/window.py
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QFileDialog

class MainWindow(QMainWindow):
    def __init__(self, on_new_window=None, *, preview_fn=preview, cache_factory=PreviewCache, viewer_factory=None, executor=None, thread_pool=None, office=None) -> None:
        file_menu = self.menuBar().addMenu("文件")
        self.actionOpen = QAction("打开", self)
        self.actionOpen.setObjectName("actionOpen")
        self.actionOpen.setShortcut(QKeySequence.StandardKey.Open)
        self.actionOpen.triggered.connect(self._open_dialog)
        file_menu.addAction(self.actionOpen)
        self.actionNewTab = QAction("+", self)
        self.actionNewTab.setObjectName("actionNewTab")
        self.actionNewTab.triggered.connect(self.add_blank_tab)
        file_menu.addAction(self.actionNewTab)
        self.actionNewWindow = QAction("新建窗口", self)
        self.actionNewWindow.setObjectName("actionNewWindow")
        self.actionNewWindow.triggered.connect(self._spawn)
        file_menu.addAction(self.actionNewWindow)

    def add_blank_tab(self) -> None:
        page = QWidget()
        page.setProperty("readerBlankTab", True)
        layout = QVBoxLayout(page)
        hint = QLabel("拖入文件，或使用 文件 → 打开")
        hint.setObjectName("blankDropHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        self._tabs.addTab(page, "未命名")
        self._tabs.setCurrentWidget(page)

    def _open_dialog(self) -> None:
        paths, _selected_filter = QFileDialog.getOpenFileNames(
            self,
            "打开",
            "",
            "Documents (*.docx *.pptx *.xlsx *.md)",
        )
        if paths:
            self.open_paths([str(path) for path in paths])
```

- [ ] **Step 4: Write failing drop replacement tests**

```python
# tests/test_window.py
def test_drop_on_blank_replaces_first_file_and_appends_extra(qtbot, tmp_path: Path):
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("1", encoding="utf-8")
    second.write_text("2", encoding="utf-8")
    window = make_window(lambda path, office=None: builtin_result(path.name))
    qtbot.addWidget(window)
    window.add_blank_tab()

    window.open_paths([str(first), str(second)], replace_blank=True)

    assert window.tab_count() == 2
    assert window.tab_title(0) == "first.md"
    assert window.tab_title(1) == "second.md"
    assert "拖入文件" not in page_text(window, 0)


def test_unsupported_drop_keeps_blank_tab(qtbot, tmp_path: Path):
    unsupported = tmp_path / "bad.pdf"
    unsupported.write_bytes(b"%PDF")
    window = make_window(lambda _path, office=None: builtin_result())
    qtbot.addWidget(window)
    window.add_blank_tab()

    window.open_paths([str(unsupported)], replace_blank=True)

    assert window.tab_count() == 1
    assert window.tab_title(0) == "未命名"
    assert "无法打开" in window.status_text()
```

- [ ] **Step 5: Run second RED command**

Run: `pytest tests/test_window.py::test_drop_on_blank_replaces_first_file_and_appends_extra tests/test_window.py::test_unsupported_drop_keeps_blank_tab -v`

Expected: FAIL because `open_paths()` does not accept `replace_blank` and cannot reuse a blank tab.

- [ ] **Step 6: Add minimal replacement implementation**

```python
# src/reader/shell/window.py
class MainWindow(QMainWindow):
    def _blank_tab_index(self) -> int | None:
        for index in range(self._tabs.count()):
            page = self._tabs.widget(index)
            if page is not None and page.property("readerBlankTab") is True:
                return index
        return None

    def open_paths(self, paths: list[str], *, replace_blank: bool = False) -> None:
        existing = [document.path for document in self._documents.values()]
        decision = decide_open(existing, [Path(path) for path in paths])
        if decision.rejected:
            rejected = ", ".join(path.name for path, _reason in decision.rejected)
            self.statusBar().showMessage(f"无法打开：{rejected}")
        if decision.to_focus is not None:
            self._focus(decision.to_focus)

        blank_index = self._blank_tab_index() if replace_blank else None
        for index, path in enumerate(decision.to_open):
            reuse_index = blank_index if index == 0 else None
            self._start_preview(path, replace_tab_index=reuse_index)

    def _start_preview(self, path: Path, *, replace_tab_index: int | None = None) -> None:
        document_id = uuid4().hex
        page = QWidget()
        layout = QVBoxLayout(page)
        loading = QLabel("正在加载…")
        loading.setObjectName("previewLoading")
        loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(loading)
        self._documents[document_id] = _Document(path=path, page=page)
        if replace_tab_index is None:
            self._tabs.addTab(page, path.name)
        else:
            old_page = self._tabs.widget(replace_tab_index)
            self._tabs.removeTab(replace_tab_index)
            if old_page is not None:
                old_page.deleteLater()
            self._tabs.insertTab(replace_tab_index, page, path.name)
        self._tabs.setCurrentWidget(page)
        self.statusBar().showMessage("正在加载…")
        self._executor.submit(document_id, path, self._preview_fn, self._office, self._cache_factory)

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.open_paths(paths, replace_blank=self._tabs.currentWidget() is not None and self._tabs.currentWidget().property("readerBlankTab") is True)
            event.acceptProposedAction()
```

- [ ] **Step 7: Run GREEN command**

Run: `pytest tests/test_window.py::test_plus_action_adds_blank_tab_with_drop_hint tests/test_window.py::test_open_action_uses_multi_select_and_adds_tabs tests/test_window.py::test_drop_on_blank_replaces_first_file_and_appends_extra tests/test_window.py::test_unsupported_drop_keeps_blank_tab tests/test_window.py::test_close_last_tab_keeps_visible_empty_window -v`

Expected: PASS. If `test_close_last_tab_keeps_visible_empty_window` still asserts `tab_title(0) == ""` after count zero, replace that assertion with `assert window.focus_path() is None` because the approved spec chose no leftover blank tab.

- [ ] **Step 8: Commit**

```bash
git add src/reader/shell/window.py tests/test_window.py
git commit -m "feat: add blank and multi-open tabs"
```

---

### Task 3: Builtin-First Preview Strategy

**Files:**
- Modify: `src/reader/preview/pipeline.py`
- Modify: `src/reader/shell/window.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_window.py`

**Interfaces:**
- Consumes: format functions `to_html(path: Path) -> PreviewResult`, `OfficeBackend.available_for(suffix: str) -> bool`, `OfficeBackend.export(path: Path) -> PreviewResult`.
- Produces: `PreviewMode = Literal["builtin", "office"]`, `def preview(path: Path, office: OfficeBackend | None = None, *, mode: PreviewMode = "builtin") -> PreviewResult`; `_PreviewWorker(..., mode: PreviewMode)`; cache strategies `"builtin"` and `"office"`.

- [ ] **Step 1: Write failing pipeline tests**

```python
# tests/test_pipeline.py
def test_docx_defaults_to_builtin_without_office_call(tmp_path: Path):
    from docx import Document

    p = tmp_path / "a.docx"
    d = Document()
    d.add_paragraph("builtin-default")
    d.save(p)
    office = FakeOffice(available=True)

    result = preview(p, office=office)

    assert office.calls == []
    assert result.status_label == "内置预览"
    assert "builtin-default" in result.html


def test_docx_explicit_office_mode_uses_export(tmp_path: Path):
    p = tmp_path / "a.docx"
    p.write_bytes(b"not-a-real-docx")
    office = FakeOffice(available=True)

    result = preview(p, office=office, mode="office")

    assert office.calls == [p]
    assert result.status_label == "Office 预览"
```

- [ ] **Step 2: Run RED command**

Run: `pytest tests/test_pipeline.py::test_docx_defaults_to_builtin_without_office_call tests/test_pipeline.py::test_docx_explicit_office_mode_uses_export -v`

Expected: FAIL because current `preview()` calls Office for Office files by default and has no `mode` keyword.

- [ ] **Step 3: Add minimal pipeline implementation**

```python
# src/reader/preview/pipeline.py
from typing import Literal, Protocol

PreviewMode = Literal["builtin", "office"]

def preview(
    path: Path,
    office: OfficeBackend | None = None,
    *,
    mode: PreviewMode = "builtin",
) -> PreviewResult:
    path = Path(path)
    suffix = sniff(path)
    if mode == "office" and suffix != ".md" and office is not None and office.available_for(suffix):
        return office.export(path)
    return _BUILTIN[suffix](path)
```

- [ ] **Step 4: Update worker mode and cache strategy tests**

```python
# tests/test_window.py
def test_window_builtin_load_uses_builtin_cache_strategy(qtbot, tmp_path: Path):
    path = tmp_path / "office.docx"
    path.write_bytes(b"x")
    cache = FakeCache()

    def preview_fn(_path: Path, office=None, mode="builtin") -> PreviewResult:
        assert mode == "builtin"
        return builtin_result("builtin")

    window = make_window(preview_fn, cache)
    qtbot.addWidget(window)

    window.open_paths([str(path)])

    qtbot.waitUntil(lambda: "builtin" in page_text(window, 0))
    assert ("get", path.resolve(), "builtin") in cache.calls
```

- [ ] **Step 5: Run worker RED command**

Run: `pytest tests/test_window.py::test_window_builtin_load_uses_builtin_cache_strategy -v`

Expected: FAIL because `_PreviewWorker` calls `preview_fn(self.path, office=self.office)` and uses cache strategy `"auto"`.

- [ ] **Step 6: Add minimal worker implementation**

```python
# src/reader/shell/window.py
from reader.preview.pipeline import PreviewMode, preview

PreviewFunction = Callable[..., PreviewResult]

class _PreviewWorker(QRunnable):
    def __init__(self, document_id: str, path: Path, preview_fn: PreviewFunction, office: Win32OfficeBackend, cache_factory: CacheFactory, signals: _WorkerSignals, mode: PreviewMode) -> None:
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
            try:
                cache = self.cache_factory()
                result = cache.get(self.path, self.mode)
            except Exception:
                cache = None
            if result is None:
                result = self.preview_fn(self.path, office=self.office, mode=self.mode)
                if cache is not None:
                    try:
                        cache.put(self.path, self.mode, result)
                    except Exception:
                        pass
            output = _pin_pdf(result)
        except Exception as exc:
            self.signals.completed.emit(self.document_id, None, exc)
            return
        self.signals.completed.emit(self.document_id, output, None)

class PreviewExecutor(QObject):
    def submit(self, document_id: str, path: Path, preview_fn: PreviewFunction, office: Win32OfficeBackend, cache_factory: CacheFactory, mode: PreviewMode = "builtin") -> None:
        signals = _WorkerSignals(self)
        worker = _PreviewWorker(document_id, path, preview_fn, office, cache_factory, signals, mode)
        signals.completed.connect(self._worker_completed, Qt.ConnectionType.QueuedConnection)
        self._workers[document_id] = worker
        self.thread_pool.start(worker)
```

- [ ] **Step 7: Run GREEN command**

Run: `pytest tests/test_pipeline.py tests/test_window.py::test_window_builtin_load_uses_builtin_cache_strategy -v`

Expected: PASS after updating older Office-first tests in `tests/test_pipeline.py` so they call `preview(p, office=office, mode="office")` when expecting Office export.

- [ ] **Step 8: Commit**

```bash
git add src/reader/preview/pipeline.py src/reader/shell/window.py tests/test_pipeline.py tests/test_window.py
git commit -m "feat: default office files to builtin preview"
```

---

### Task 4: Office High-Fidelity Switch Per Tab

**Files:**
- Modify: `src/reader/shell/window.py`
- Modify: `tests/test_window.py`

**Interfaces:**
- Consumes: `preview(path, office=..., mode="office") -> PreviewResult`, `Win32OfficeBackend.available_for(suffix: str) -> bool`.
- Produces: `_Document.mode: PreviewMode`, `_Document.last_result: PreviewResult | None`, `def MainWindow.switch_current_tab_to_office() -> None`, `def MainWindow.switch_current_tab_to_builtin() -> None`, `MainWindow.actionOfficePreview`, `MainWindow.actionBuiltinPreview`.

- [ ] **Step 1: Write failing availability and action tests**

```python
# tests/test_window.py
class FakeOfficeAvailability:
    def __init__(self, available: bool) -> None:
        self.available = available
        self.calls: list[str] = []

    def available_for(self, suffix: str) -> bool:
        self.calls.append(suffix)
        return self.available

    def export(self, path: Path) -> PreviewResult:
        return PreviewResult(html="<p>office</p>", status_label="Office 预览", kind="html")


def test_office_action_disabled_when_office_missing(qtbot, tmp_path: Path):
    path = tmp_path / "doc.docx"
    path.write_bytes(b"x")
    office = FakeOfficeAvailability(False)
    window = MainWindow(
        preview_fn=lambda _path, office=None, mode="builtin": builtin_result("builtin"),
        cache_factory=FakeCache,
        viewer_factory=label_viewer,
        office=office,
    )
    qtbot.addWidget(window)

    window.open_paths([str(path)])

    qtbot.waitUntil(lambda: "builtin" in page_text(window, 0))
    assert window.actionOfficePreview.isEnabled() is False
    assert window.actionOfficePreview.toolTip() == "未检测到 Microsoft Office"
```

- [ ] **Step 2: Run RED command**

Run: `pytest tests/test_window.py::test_office_action_disabled_when_office_missing -v`

Expected: FAIL because `actionOfficePreview` does not exist.

- [ ] **Step 3: Add minimal Office/Builtin actions**

```python
# src/reader/shell/window.py
@dataclass
class _Document:
    path: Path
    page: QWidget
    artifact_dir: Path | None = None
    mode: PreviewMode = "builtin"
    last_result: PreviewResult | None = None

class MainWindow(QMainWindow):
    def __init__(self, on_new_window=None, *, preview_fn=preview, cache_factory=PreviewCache, viewer_factory=None, executor=None, thread_pool=None, office=None) -> None:
        self.actionOfficePreview = QAction("Office 高保真", self)
        self.actionOfficePreview.setObjectName("actionOfficePreview")
        self.actionOfficePreview.triggered.connect(self.switch_current_tab_to_office)
        self.actionBuiltinPreview = QAction("内置预览", self)
        self.actionBuiltinPreview.setObjectName("actionBuiltinPreview")
        self.actionBuiltinPreview.triggered.connect(self.switch_current_tab_to_builtin)
        self.menuBar().addMenu("预览").addActions([self.actionOfficePreview, self.actionBuiltinPreview])
        self._tabs.currentChanged.connect(lambda _index: self._refresh_preview_actions())
        self._refresh_preview_actions()

    def _current_document_id(self) -> str | None:
        page = self._tabs.currentWidget()
        for document_id, document in self._documents.items():
            if document.page is page:
                return document_id
        return None

    def _refresh_preview_actions(self) -> None:
        document_id = self._current_document_id()
        document = self._documents.get(document_id) if document_id is not None else None
        office_enabled = False
        if document is not None and document.path.suffix.lower() in {".docx", ".pptx", ".xlsx"}:
            office_enabled = self._office.available_for(document.path.suffix.lower())
        self.actionOfficePreview.setEnabled(office_enabled)
        self.actionOfficePreview.setToolTip("" if office_enabled else "未检测到 Microsoft Office")
        self.actionBuiltinPreview.setEnabled(document is not None and document.mode != "builtin")
```

- [ ] **Step 4: Write failing switch and failure-preserve tests**

```python
# tests/test_window.py
def test_switch_to_office_replaces_viewer_and_status(qtbot, tmp_path: Path):
    path = tmp_path / "doc.docx"
    path.write_bytes(b"x")
    modes: list[str] = []

    def preview_fn(_path: Path, office=None, mode="builtin") -> PreviewResult:
        modes.append(mode)
        if mode == "office":
            return PreviewResult(html="<p>office-ready</p>", status_label="Office 预览", kind="html")
        return builtin_result("builtin-ready")

    window = MainWindow(preview_fn=preview_fn, cache_factory=FakeCache, viewer_factory=label_viewer, office=FakeOfficeAvailability(True))
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: "builtin-ready" in page_text(window, 0))

    window.switch_current_tab_to_office()

    qtbot.waitUntil(lambda: "office-ready" in page_text(window, 0))
    assert modes == ["builtin", "office"]
    assert "Office 预览" in window.status_text()


def test_office_failure_keeps_builtin_content(qtbot, tmp_path: Path):
    path = tmp_path / "doc.docx"
    path.write_bytes(b"x")

    def preview_fn(_path: Path, office=None, mode="builtin") -> PreviewResult:
        if mode == "office":
            raise RuntimeError("COM failed")
        return builtin_result("builtin-stays")

    window = MainWindow(preview_fn=preview_fn, cache_factory=FakeCache, viewer_factory=label_viewer, office=FakeOfficeAvailability(True))
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: "builtin-stays" in page_text(window, 0))

    window.switch_current_tab_to_office()

    qtbot.waitUntil(lambda: "Office 导出失败" in window.status_text())
    assert "builtin-stays" in page_text(window, 0)
```

- [ ] **Step 5: Run second RED command**

Run: `pytest tests/test_window.py::test_switch_to_office_replaces_viewer_and_status tests/test_window.py::test_office_failure_keeps_builtin_content -v`

Expected: FAIL because switching modes is not wired.

- [ ] **Step 6: Add minimal switching implementation**

```python
# src/reader/shell/window.py
class MainWindow(QMainWindow):
    def switch_current_tab_to_office(self) -> None:
        document_id = self._current_document_id()
        if document_id is None:
            return
        document = self._documents[document_id]
        if not self._office.available_for(document.path.suffix.lower()):
            self._refresh_preview_actions()
            return
        self._restart_preview(document_id, "office")

    def switch_current_tab_to_builtin(self) -> None:
        document_id = self._current_document_id()
        if document_id is None:
            return
        self._restart_preview(document_id, "builtin")

    def _restart_preview(self, document_id: str, mode: PreviewMode) -> None:
        document = self._documents[document_id]
        self._executor.cancel(document_id)
        _cleanup_dir(document.artifact_dir)
        document.artifact_dir = None
        document.mode = mode
        self.statusBar().showMessage("正在加载…")
        self._executor.submit(document_id, document.path, self._preview_fn, self._office, self._cache_factory, mode)

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
        if error is not None and document is not None and document.mode == "office" and document.last_result is not None:
            self.statusBar().showMessage("内置预览（Office 导出失败）")
            document.mode = "builtin"
            self._refresh_preview_actions()
            return

        if error is not None:
            content: QWidget = QLabel(str(error))
            content.setObjectName("previewContent")
            status = f"预览失败：{document.path.name}"
        elif output is None:
            content = QLabel("未返回预览结果")
            content.setObjectName("previewContent")
            status = f"预览失败：{document.path.name}"
        elif output.result.kind == "error":
            content = QLabel(output.result.error or "error")
            content.setObjectName("previewContent")
            status = output.result.status_label
        else:
            try:
                content = self._viewer_factory(output.result, document.path)
                status = output.result.status_label
            except Exception as exc:
                _cleanup_dir(output.artifact_dir)
                content = QLabel(str(exc))
                content.setObjectName("previewContent")
                status = f"预览失败：{document.path.name}"
                output = None

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
            document.last_result = output.result
        self.statusBar().showMessage(status)
        self._refresh_preview_actions()
```

- [ ] **Step 7: Run GREEN command**

Run: `pytest tests/test_window.py::test_office_action_disabled_when_office_missing tests/test_window.py::test_switch_to_office_replaces_viewer_and_status tests/test_window.py::test_office_failure_keeps_builtin_content -v`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/reader/shell/window.py tests/test_window.py
git commit -m "feat: add office high fidelity switch"
```

---

### Task 5: Transparent R Icon Assets

**Files:**
- Create: `assets/icons/reader-r.svg`
- Create: `scripts/generate_icons.py`
- Create: `assets/icons/reader-16.png`
- Create: `assets/icons/reader-24.png`
- Create: `assets/icons/reader-32.png`
- Create: `assets/icons/reader-48.png`
- Create: `assets/icons/reader-256.png`
- Create: `assets/icons/reader.ico`
- Modify: `pyproject.toml`
- Create: `tests/test_icon_assets.py`

**Interfaces:**
- Consumes: no runtime Reader interface.
- Produces: `ICON_SIZES: tuple[int, ...] = (16, 24, 32, 48, 256)`, `def generate_icon_assets(root: Path) -> list[Path]`; asset paths under `assets/icons/`.

- [ ] **Step 1: Write failing icon asset tests**

```python
# tests/test_icon_assets.py
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "assets" / "icons"


def test_icon_files_exist():
    expected = [
        "reader-r.svg",
        "reader-16.png",
        "reader-24.png",
        "reader-32.png",
        "reader-48.png",
        "reader-256.png",
        "reader.ico",
    ]
    assert [name for name in expected if not (ICON_DIR / name).exists()] == []


def test_png_alpha_is_transparent_outside_and_inside_counter():
    image = Image.open(ICON_DIR / "reader-256.png").convert("RGBA")
    assert image.getpixel((8, 8))[3] == 0
    assert image.getpixel((154, 84))[3] == 0
    assert image.getpixel((78, 128))[3] == 255


def test_ico_contains_multiple_transparent_sizes():
    icon = Image.open(ICON_DIR / "reader.ico")
    assert {size for size in icon.ico.sizes()} >= {(16, 16), (24, 24), (32, 32), (48, 48), (256, 256)}
```

- [ ] **Step 2: Run RED command**

Run: `pytest tests/test_icon_assets.py -v`

Expected: FAIL because `assets/icons/` and generated assets do not exist.

- [ ] **Step 3: Add Pillow dev dependency**

```toml
# pyproject.toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-qt>=4.4", "pytest-mock>=3.14", "Pillow>=10.0"]
```

- [ ] **Step 4: Add reviewable SVG source**

```xml
<!-- assets/icons/reader-r.svg -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <title>Reader rounded-ribbon R</title>
  <desc>Transparent field with saturated blue rounded uppercase R strokes.</desc>
  <g fill="none" stroke="#2563EB" stroke-width="34" stroke-linecap="round" stroke-linejoin="round">
    <path d="M72 216V40"/>
    <path d="M72 40H142C180 40 204 62 204 95C204 128 180 150 142 150H72"/>
    <path d="M138 150L204 216"/>
  </g>
</svg>
```

- [ ] **Step 5: Add deterministic Pillow generator**

```python
# scripts/generate_icons.py
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ICON_SIZES: tuple[int, ...] = (16, 24, 32, 48, 256)
BLUE = (37, 99, 235, 255)


def _scale(points: list[tuple[float, float]], size: int) -> list[tuple[int, int]]:
    factor = size / 256
    return [(round(x * factor), round(y * factor)) for x, y in points]


def _draw_reader_r(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    width = max(2, round(34 * size / 256))
    draw.line(_scale([(72, 216), (72, 40)], size), fill=BLUE, width=width, joint="curve")
    draw.line(_scale([(72, 40), (142, 40), (204, 95), (142, 150), (72, 150)], size), fill=BLUE, width=width, joint="curve")
    draw.line(_scale([(138, 150), (204, 216)], size), fill=BLUE, width=width, joint="curve")
    return image


def generate_icon_assets(root: Path) -> list[Path]:
    icon_dir = root / "assets" / "icons"
    icon_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    images: list[Image.Image] = []
    for size in ICON_SIZES:
        image = _draw_reader_r(size)
        path = icon_dir / f"reader-{size}.png"
        image.save(path)
        outputs.append(path)
        images.append(image)
    ico_path = icon_dir / "reader.ico"
    images[-1].save(ico_path, sizes=[(size, size) for size in ICON_SIZES], append_images=images[:-1])
    outputs.append(ico_path)
    return outputs


if __name__ == "__main__":
    for generated in generate_icon_assets(Path(__file__).resolve().parents[1]):
        print(generated)
```

- [ ] **Step 6: Generate assets**

Run: `python scripts/generate_icons.py`

Expected: prints paths for the five PNG files and `assets/icons/reader.ico`; command exits with code 0.

- [ ] **Step 7: Run GREEN command**

Run: `pytest tests/test_icon_assets.py -v`

Expected: PASS with alpha 0 outside the glyph and inside the R counter.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml scripts/generate_icons.py assets/icons/reader-r.svg assets/icons/reader-16.png assets/icons/reader-24.png assets/icons/reader-32.png assets/icons/reader-48.png assets/icons/reader-256.png assets/icons/reader.ico tests/test_icon_assets.py
git commit -m "feat: add transparent reader icon assets"
```

---

### Task 6: Shell Registration Uses Reader.exe and Icons

**Files:**
- Modify: `src/reader/shell/associate.py`
- Modify: `src/reader/__main__.py`
- Create: `tests/test_main_launch.py`
- Modify: `tests/test_associate.py`

**Interfaces:**
- Consumes: current `register_open_with(exe: str, winreg_module=None) -> None`, `create_desktop_shortcut(exe: str, name: str = "Reader", winshell_or_com=None) -> Path`.
- Produces: `def _association_target() -> tuple[str, tuple[str, ...]]`, `def register_open_with(exe: str, *, args: tuple[str, ...] = (), winreg_module=None) -> None`, `def create_desktop_shortcut(exe: str, name: str = "Reader", *, args: tuple[str, ...] = (), icon: str | None = None, winshell_or_com=None) -> Path`, `DefaultIcon` registry value set to icon/exe path, shortcut `IconLocation` set to icon/exe path.

- [ ] **Step 1: Write failing association icon tests**

```python
# tests/test_associate.py
class FakeShortcut:
    def __init__(self) -> None:
        self.Targetpath = ""
        self.Arguments = ""
        self.WorkingDirectory = ""
        self.Description = ""
        self.IconLocation = ""
        self.saved = False

    def Save(self) -> None:
        self.saved = True


def test_register_open_with_sets_default_icon_to_exe() -> None:
    wr = FakeWinreg()
    register_open_with(r"C:\Reader\Reader.exe", winreg_module=wr)

    assert wr.keys[r"Software\Classes\Reader.Document\DefaultIcon"].values[None] == r"C:\Reader\Reader.exe"
    assert wr.keys[r"Software\Classes\Reader.Document\shell\open\command"].values[None] == r'"C:\Reader\Reader.exe" "%1"'


def test_register_open_with_formats_development_python_module_command() -> None:
    wr = FakeWinreg()
    register_open_with(r"C:\Python312\python.exe", args=("-m", "reader"), winreg_module=wr)

    assert wr.keys[r"Software\Classes\Reader.Document\DefaultIcon"].values[None] == r"C:\Python312\python.exe"
    assert wr.keys[r"Software\Classes\Reader.Document\shell\open\command"].values[None] == r'"C:\Python312\python.exe" -m reader "%1"'


def test_create_desktop_shortcut_sets_icon_location(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("reader.shell.associate._desktop_known_location", lambda: tmp_path / "KnownDesktop")
    com = FakeComModule()

    create_desktop_shortcut(r"C:\Reader\Reader.exe", winshell_or_com=com)

    shortcut = com.shell.shortcuts[0]
    assert shortcut.Targetpath == r"C:\Reader\Reader.exe"
    assert shortcut.WorkingDirectory == r"C:\Reader"
    assert shortcut.IconLocation == r"C:\Reader\Reader.exe"
```

- [ ] **Step 2: Run association RED command**

Run: `pytest tests/test_associate.py::test_register_open_with_sets_default_icon_to_exe tests/test_associate.py::test_create_desktop_shortcut_sets_icon_location -v`

Expected: FAIL because `DefaultIcon` and shortcut `IconLocation` are not written.

- [ ] **Step 3: Implement icon shell registration**

```python
# src/reader/shell/associate.py
def _quote_arg(value: str) -> str:
    return f'"{value}"' if " " in value else value


def register_open_with(exe: str, *, args: tuple[str, ...] = (), winreg_module=None) -> None:
    import winreg as default_winreg

    wr = winreg_module or default_winreg
    command_parts = [f'"{exe}"', *[_quote_arg(arg) for arg in args], '"%1"']
    command = " ".join(command_parts)
    _set_reg_sz(wr, r"Software\Classes\Reader.Document\DefaultIcon", None, exe)
    _set_reg_sz(wr, r"Software\Classes\Reader.Document\shell\open\command", None, command)
    for ext in EXTENSIONS:
        _set_reg_sz(wr, rf"Software\Classes\{ext}\OpenWithProgids", PROGID, "")


def create_desktop_shortcut(
    exe: str,
    name: str = "Reader",
    *,
    args: tuple[str, ...] = (),
    icon: str | None = None,
    winshell_or_com=None,
) -> Path:
    desktop = _desktop_path()
    desktop.mkdir(parents=True, exist_ok=True)
    shortcut_path = desktop / f"{name}.lnk"
    if winshell_or_com is None:
        import win32com.client as winshell_or_com
    shell = winshell_or_com.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.Targetpath = exe
    shortcut.Arguments = " ".join(_quote_arg(arg) for arg in args)
    shortcut.WorkingDirectory = str(Path(exe).parent)
    shortcut.Description = name
    shortcut.IconLocation = icon or exe
    save = getattr(shortcut, "Save", None) or getattr(shortcut, "save")
    save()
    return shortcut_path
```

- [ ] **Step 4: Write failing frozen/development target tests**

```python
# tests/test_main_launch.py
import sys


def test_launch_target_uses_frozen_executable(monkeypatch):
    import reader.__main__ as main_module

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Reader\Reader.exe")

    assert main_module._association_target() == (r"C:\Reader\Reader.exe", ())


def test_launch_target_uses_python_m_reader_in_development(monkeypatch):
    import reader.__main__ as main_module

    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Python312\python.exe")

    assert main_module._association_target() == (r"C:\Python312\python.exe", ("-m", "reader"))
```

- [ ] **Step 5: Run launch RED command**

Run: `pytest tests/test_main_launch.py -v`

Expected: FAIL because `__main__._launch_target()` points development at `scripts/reader.cmd` and there is no `_association_target()`.

- [ ] **Step 6: Implement frozen/development association target**

```python
# src/reader/__main__.py
def _association_target() -> tuple[str, tuple[str, ...]]:
    if getattr(sys, "frozen", False):
        return sys.executable, ()
    return sys.executable, ("-m", "reader")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    files = [arg for arg in argv[1:] if not arg.startswith("-")]
    set_app_user_model_id()
    if _server_running():
        SingleInstance.send_paths(files)
        return 0
    qapp = QApplication.instance() or QApplication(argv)
    app = ReaderApp(qapp)
    if not app.is_primary_instance():
        SingleInstance.send_paths(files)
        return 0
    win = app.new_window()
    if files:
        win.open_paths(files)
    try:
        exe, args = _association_target()
        register_open_with(exe, args=args)
        create_desktop_shortcut(exe, args=args, icon=exe)
    except Exception:
        pass
    return qapp.exec()
```

- [ ] **Step 7: Run GREEN command**

Run: `pytest tests/test_associate.py tests/test_main_launch.py -v`

Expected: PASS and no test writes `UserChoice`.

- [ ] **Step 8: Commit**

```bash
git add src/reader/shell/associate.py src/reader/__main__.py tests/test_associate.py tests/test_main_launch.py
git commit -m "feat: register reader exe and icons"
```

---

### Task 7: PyInstaller Onedir Packaging

**Files:**
- Create: `reader.spec`
- Create: `version_info.txt`
- Create: `scripts/build_windows.ps1`
- Create: `tests/test_packaging.py`

**Interfaces:**
- Consumes: `assets/icons/reader.ico`, package entry `reader.__main__.main`.
- Produces: PyInstaller output `dist/Reader/Reader.exe`; `scripts/build_windows.ps1` install/build command.

- [ ] **Step 1: Write failing packaging tests**

```python
# tests/test_packaging.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_reader_spec_references_onedir_icon_version_and_webengine():
    spec = (ROOT / "reader.spec").read_text(encoding="utf-8")
    assert "name='Reader'" in spec
    assert "console=False" in spec
    assert "assets/icons/reader.ico" in spec.replace("\\\\", "/")
    assert "version_info.txt" in spec
    assert "collect_data_files('PySide6'" in spec
    assert "QtWebEngine" in spec


def test_build_windows_script_installs_dev_pyinstaller_and_runs_spec():
    script = (ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")
    assert 'pip install -e ".[dev]" pyinstaller' in script
    assert "pyinstaller reader.spec --noconfirm" in script
    assert "dist\\Reader\\Reader.exe" in script
```

- [ ] **Step 2: Run RED command**

Run: `pytest tests/test_packaging.py -v`

Expected: FAIL because `reader.spec`, `version_info.txt`, and `scripts/build_windows.ps1` do not exist.

- [ ] **Step 3: Add PyInstaller version resource**

```python
# version_info.txt
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(0, 1, 0, 0),
    prodvers=(0, 1, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'Reader'),
          StringStruct('FileDescription', 'Reader'),
          StringStruct('FileVersion', '0.1.0'),
          StringStruct('InternalName', 'Reader'),
          StringStruct('OriginalFilename', 'Reader.exe'),
          StringStruct('ProductName', 'Reader'),
          StringStruct('ProductVersion', '0.1.0')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
```

- [ ] **Step 4: Add onedir spec**

```python
# reader.spec
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

pyside6_datas = collect_data_files('PySide6', includes=['Qt/resources/*', 'Qt/translations/*', 'QtWebEngineProcess.exe', 'Qt/libexec/*', 'Qt/bin/QtWebEngineProcess.exe'])
pyside6_hidden = collect_submodules('PySide6.QtWebEngineCore') + collect_submodules('PySide6.QtWebEngineWidgets')

a = Analysis(
    ['src/reader/__main__.py'],
    pathex=[],
    binaries=[],
    datas=pyside6_datas + [('assets/icons/reader.ico', 'assets/icons'), ('assets/icons/reader-r.svg', 'assets/icons')],
    hiddenimports=pyside6_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Reader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/icons/reader.ico',
    version='version_info.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Reader',
)
```

- [ ] **Step 5: Add Windows build script**

```powershell
# scripts/build_windows.ps1
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
}

$Python = Resolve-Path ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -e ".[dev]" pyinstaller
& $Python scripts\generate_icons.py
& $Python -m PyInstaller reader.spec --noconfirm

if (-not (Test-Path "dist\Reader\Reader.exe")) {
    throw "dist\Reader\Reader.exe was not produced"
}

Write-Host "Built dist\Reader\Reader.exe"
```

- [ ] **Step 6: Run GREEN command**

Run: `pytest tests/test_packaging.py -v`

Expected: PASS.

- [ ] **Step 7: Manual packaging smoke command**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1`

Expected: command exits with code 0 and prints `Built dist\Reader\Reader.exe`. If PyInstaller is unavailable on the machine, keep the static tests passing and record the local environment failure in the task notes before review.

- [ ] **Step 8: Commit**

```bash
git add reader.spec version_info.txt scripts/build_windows.ps1 tests/test_packaging.py
git commit -m "feat: add windows onedir packaging"
```

---

### Task 8: Rapid Multi-Launch IPC and Multi-Arg Regression

**Files:**
- Modify: `src/reader/ipc.py`
- Modify: `src/reader/__main__.py`
- Modify: `tests/test_ipc.py`
- Modify: `tests/test_window.py`

**Interfaces:**
- Consumes: `SingleInstance.send_paths(paths: list[str]) -> bool`, `SingleInstance.become_server(on_paths: Callable[[list[str]], None]) -> bool`, `ReaderApp._on_ipc_paths(paths: list[str]) -> None`.
- Produces: reliable handling for several fast sequential `send_paths()` calls and multiple paths in one argv list.

- [ ] **Step 1: Write failing rapid IPC tests**

```python
# tests/test_ipc.py
def test_e2e_rapid_sequential_open_with_launches(monkeypatch: pytest.MonkeyPatch, tmp_path):
    _patch_unique_server(monkeypatch, tmp_path)
    assert ipc_module.POST_SEND_EVENT_PUMPS == 3
    seen: list[list[str]] = []
    inst = SingleInstance()
    try:
        assert inst.become_server(lambda paths: seen.append(paths)) is True
        payloads = [[f"C:/tmp/{index}.md"] for index in range(8)]
        for payload in payloads:
            assert SingleInstance.send_paths(payload) is True
        assert _wait_until(lambda: len(seen) == len(payloads), timeout_s=8.0)
        assert seen == payloads
    finally:
        inst.close()
```

- [ ] **Step 2: Run RED command**

Run: `pytest tests/test_ipc.py::test_e2e_rapid_sequential_open_with_launches -v`

Expected: FAIL with `AttributeError: module 'reader.ipc' has no attribute 'POST_SEND_EVENT_PUMPS'`.

- [ ] **Step 3: Add conservative IPC drain after send**

```python
# src/reader/ipc.py
POST_SEND_EVENT_PUMPS = 3


class SingleInstance:
    @staticmethod
    def send_paths(paths: list[str]) -> bool:
        sock: QLocalSocket | None = None
        for attempt in range(_CONNECT_ATTEMPTS):
            SingleInstance._pump_events()
            candidate = QLocalSocket()
            candidate.connectToServer(SERVER_NAME)
            if candidate.waitForConnected(_CONNECT_TIMEOUT_MS):
                sock = candidate
                break
            candidate.disconnectFromServer()
            if attempt + 1 < _CONNECT_ATTEMPTS:
                SingleInstance._pump_events()
                time.sleep(0.025 * (attempt + 1))
        if sock is None:
            return False

        payload = json.dumps([str(p) for p in paths], ensure_ascii=False).encode("utf-8")
        frame = struct.pack(">I", len(payload)) + payload
        total_written = 0
        while total_written < len(frame):
            remaining = frame[total_written:]
            if SEND_CHUNK_BYTES is not None and SEND_CHUNK_BYTES > 0:
                remaining = remaining[:SEND_CHUNK_BYTES]
            written = sock.write(remaining)
            if written < 0:
                sock.disconnectFromServer()
                return False
            if written == 0 and not sock.waitForBytesWritten(_WRITE_TIMEOUT_MS):
                sock.disconnectFromServer()
                return False
            total_written += written

        if hasattr(sock, "flush"):
            sock.flush()
        for _ in range(POST_SEND_EVENT_PUMPS):
            SingleInstance._pump_events()
            if sock.bytesToWrite() == 0:
                break
            if not sock.waitForBytesWritten(_WRITE_TIMEOUT_MS):
                sock.disconnectFromServer()
                return False
        sock.disconnectFromServer()
        SingleInstance._pump_events()
        return True
```

- [ ] **Step 4: Write failing multi-argv app test**

```python
# tests/test_window.py
def test_ipc_callback_opens_all_forwarded_paths(reader_app, qtbot, tmp_path: Path):
    app, ipc = reader_app
    first = tmp_path / "a.md"
    second = tmp_path / "b.md"
    first.write_text("a", encoding="utf-8")
    second.write_text("b", encoding="utf-8")
    window = app.new_window()
    window._preview_fn = lambda path, office=None, mode="builtin": builtin_result(path.name)
    window._viewer_factory = label_viewer
    window._cache_factory = FakeCache

    ipc.on_paths([str(first), str(second)])

    assert window.tab_count() == 2
    qtbot.waitUntil(lambda: "b.md" in page_text(window, 1))
```

- [ ] **Step 5: Run app regression command**

Run: `pytest tests/test_window.py::test_ipc_callback_opens_all_forwarded_paths -v`

Expected: PASS if current `ReaderApp._on_ipc_paths()` already forwards all paths; keep it as a regression. If it fails, fix `_on_ipc_paths()` to call `window.open_paths(paths)` once with the complete list.

- [ ] **Step 6: Run GREEN command**

Run: `pytest tests/test_ipc.py::test_e2e_rapid_sequential_open_with_launches tests/test_window.py::test_ipc_callback_opens_all_forwarded_paths -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/reader/ipc.py src/reader/__main__.py tests/test_ipc.py tests/test_window.py
git commit -m "test: cover rapid open-with forwarding"
```

---

### Task 9: Full UX and Packaging Regression

**Files:**
- Modify: `tests/test_window.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_associate.py`
- Modify: `tests/test_icon_assets.py`
- Modify: `tests/test_packaging.py`

**Interfaces:**
- Consumes: all interfaces produced by Tasks 1-8.
- Produces: final regression suite covering window UX, preview policy, shell registration, icon alpha, packaging statics, and IPC.

- [ ] **Step 1: Add final cross-feature regression tests**

```python
# tests/test_window.py
def test_ux_packaging_regression_multi_open_duplicate_blank_and_office_failure(qtbot, tmp_path: Path):
    first = tmp_path / "first.docx"
    second = tmp_path / "second.md"
    first.write_bytes(b"x")
    second.write_text("second", encoding="utf-8")

    def preview_fn(path: Path, office=None, mode="builtin") -> PreviewResult:
        if mode == "office":
            raise RuntimeError("COM failed")
        return builtin_result(path.name)

    window = MainWindow(preview_fn=preview_fn, cache_factory=FakeCache, viewer_factory=label_viewer, office=FakeOfficeAvailability(True))
    qtbot.addWidget(window)
    window.add_blank_tab()
    window.open_paths([str(first), str(second), str(first)], replace_blank=True)
    qtbot.waitUntil(lambda: window.tab_count() == 2)

    assert window.tab_title(0) == "first.docx"
    assert window.tab_title(1) == "second.md"
    assert window.focus_path() == str(first.resolve())
    window.switch_current_tab_to_office()
    qtbot.waitUntil(lambda: "Office 导出失败" in window.status_text())
    assert "first.docx" in page_text(window, 0)
```

- [ ] **Step 2: Run focused regression command**

Run: `pytest tests/test_window.py::test_ux_packaging_regression_multi_open_duplicate_blank_and_office_failure -v`

Expected: PASS if Tasks 1-8 are complete. If it fails, the failure identifies a regression in the task that owns the reported interface.

- [ ] **Step 3: Run full unit suite**

Run: `pytest -v`

Expected: PASS for all non-Office tests. Tests marked `office` remain skipped on hosts without Microsoft Office.

- [ ] **Step 4: Run icon generator idempotence check**

Run: `python scripts/generate_icons.py`

Expected: exits with code 0 and rewrites the same deterministic asset filenames.

- [ ] **Step 5: Run packaging static checks**

Run: `pytest tests/test_packaging.py tests/test_icon_assets.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_window.py tests/test_pipeline.py tests/test_associate.py tests/test_icon_assets.py tests/test_packaging.py
git commit -m "test: add reader ux packaging regression"
```

---

## Self-Review

- Spec coverage: Tasks 1-2 cover 1200×800 centered window, 800×500 minimum, blank `+` tab, Open multi-select, drop blank replacement, extra append, duplicate focus, and no leftover blank after last close. Tasks 3-4 cover builtin-first Office preview, explicit Office 高保真 switching, disabled action when COM is unavailable, worker-thread COM path, failure preserving builtin content, and switch-back support. Task 5 covers concept C transparent blue R SVG/PNG/ICO generation and alpha tests. Task 6 covers application/window/shortcut/ProgID icons, `DefaultIcon`, frozen exe association, and development `python -m reader`. Task 7 covers PyInstaller onedir, spec, version resource, build script, WebEngine collection, and `Reader.exe`. Task 8 covers multi-argv and rapid second-launch IPC. Task 9 covers regression execution.
- Placeholder scan: the plan contains concrete file paths, concrete signatures, exact commands, expected results, and executable code blocks for every task.
- Type consistency: `PreviewMode` is introduced once as `Literal["builtin", "office"]` and reused by `preview()`, `_PreviewWorker`, `PreviewExecutor.submit()`, `_Document.mode`, and `MainWindow._restart_preview()`. `open_paths(paths: list[str], *, replace_blank: bool = False)` remains backward-compatible with existing callers. `register_open_with(exe: str)` and `create_desktop_shortcut(exe: str)` keep their public parameters while adding icon writes.

