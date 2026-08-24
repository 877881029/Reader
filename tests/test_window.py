from __future__ import annotations

import gc
import platform
import threading
import uuid
from pathlib import Path

import pytest
from PySide6.QtCore import QMimeData, QPoint, QThread, QUrl
from PySide6.QtWidgets import QLabel

from reader.preview.result import PreviewResult


class FakeIpc:
    active = False

    def __init__(self) -> None:
        self.become_calls = 0
        self.closed = False
        self.on_paths = None
        self.owns_server = False

    def become_server(self, on_paths):
        self.become_calls += 1
        self.on_paths = on_paths
        if FakeIpc.active:
            return False
        FakeIpc.active = True
        self.owns_server = True
        return True

    def close(self) -> None:
        self.closed = True
        if self.owns_server:
            FakeIpc.active = False
            self.owns_server = False


class FakeCache:
    def __init__(self, hit: PreviewResult | None = None, fail: bool = False) -> None:
        self.hit = hit
        self.fail = fail
        self.calls: list[tuple[str, Path, str]] = []

    def get(self, path: Path, strategy: str) -> PreviewResult | None:
        self.calls.append(("get", path, strategy))
        if self.fail:
            raise OSError("cache unavailable")
        return self.hit

    def put(self, path: Path, strategy: str, result: PreviewResult) -> None:
        self.calls.append(("put", path, strategy))
        if self.fail:
            raise OSError("cache unavailable")


class FakeOfficeAvailability:
    def __init__(self, available: bool) -> None:
        self.available = available
        self.calls: list[str] = []
        self.thread_ids: list[int] = []

    def available_for(self, suffix: str) -> bool:
        self.calls.append(suffix)
        self.thread_ids.append(threading.get_ident())
        return self.available

    def export(self, path: Path) -> PreviewResult:
        return PreviewResult(html="<p>office</p>", status_label="Office 预览", kind="html")


def label_viewer(result: PreviewResult, _source_path: Path | None = None) -> QLabel:
    label = QLabel(result.error or result.html)
    label.setObjectName("previewContent")
    return label


def builtin_result(text: str = "ready") -> PreviewResult:
    return PreviewResult(html=text, status_label="内置预览")


@pytest.fixture
def reader_app(qapp):
    from reader.app import ReaderApp

    ipc = FakeIpc()
    app = ReaderApp(qapp, ipc=ipc)
    yield app, ipc
    app.close_all()


@pytest.fixture(autouse=True)
def disable_host_office_detection(monkeypatch):
    monkeypatch.setattr(
        "reader.shell.window.Win32OfficeBackend.available_for",
        lambda _self, _suffix: False,
    )


def make_window(preview_fn, cache=None):
    from reader.shell.window import MainWindow

    return MainWindow(
        preview_fn=preview_fn,
        cache_factory=lambda: cache or FakeCache(),
        viewer_factory=label_viewer,
    )


def page_text(window, index: int) -> str:
    page = window._tabs.widget(index)
    labels = page.findChildren(QLabel)
    return " ".join(label.text() for label in labels)


def test_open_paths_returns_while_preview_worker_is_blocked(qtbot, tmp_path: Path):
    path = tmp_path / "slow.md"
    path.write_text("# slow", encoding="utf-8")
    started = threading.Event()
    release = threading.Event()
    worker_thread_ids: list[int] = []
    viewer_thread_ids: list[QThread] = []

    def blocked_preview(_path: Path, office=None, mode="builtin") -> PreviewResult:
        worker_thread_ids.append(threading.get_ident())
        started.set()
        assert release.wait(10)
        return builtin_result()

    def thread_checking_viewer(result: PreviewResult, _source_path: Path) -> QLabel:
        viewer_thread_ids.append(QThread.currentThread())
        return label_viewer(result)

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=blocked_preview,
        cache_factory=FakeCache,
        viewer_factory=thread_checking_viewer,
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])

    try:
        assert release.is_set() is False
        assert window.tab_count() == 1
        assert window.tab_title(0) == "slow.md"
        assert "正在加载" in page_text(window, 0)
        assert window._executor.active_count() == 1
        qtbot.waitUntil(started.is_set, timeout=10_000)
        assert release.is_set() is False
        assert worker_thread_ids != [threading.get_ident()]
        assert window._executor.thread_pool.maxThreadCount() == 1
        gc.collect()
        assert window._executor.active_count() == 1
    finally:
        release.set()

    qtbot.waitUntil(lambda: "ready" in page_text(window, 0))
    qtbot.waitUntil(lambda: window._executor.active_count() == 0)
    gc.collect()
    assert viewer_thread_ids == [window.thread()]
    assert "内置预览" in window.status_text()


def test_cache_hit_skips_preview_and_cache_miss_puts(qtbot, tmp_path: Path):
    hit_path = tmp_path / "hit.md"
    miss_path = tmp_path / "miss.md"
    hit_path.write_text("hit", encoding="utf-8")
    miss_path.write_text("miss", encoding="utf-8")
    hit_cache = FakeCache(hit=builtin_result("cached"))
    miss_cache = FakeCache()
    preview_calls: list[Path] = []

    def preview_fn(path: Path, office=None, mode="builtin") -> PreviewResult:
        preview_calls.append(path)
        return builtin_result("generated")

    hit_window = make_window(preview_fn, hit_cache)
    miss_window = make_window(preview_fn, miss_cache)
    qtbot.addWidget(hit_window)
    qtbot.addWidget(miss_window)
    hit_window.open_paths([str(hit_path)])
    miss_window.open_paths([str(miss_path)])

    qtbot.waitUntil(lambda: "cached" in page_text(hit_window, 0))
    qtbot.waitUntil(lambda: "generated" in page_text(miss_window, 0))
    assert preview_calls == [miss_path.resolve()]
    assert hit_cache.calls == [("get", hit_path.resolve(), "builtin")]
    assert [call[0] for call in miss_cache.calls] == ["get", "put"]


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


def test_office_action_disabled_when_office_missing(qtbot, tmp_path: Path):
    path = tmp_path / "doc.docx"
    path.write_bytes(b"x")
    office = FakeOfficeAvailability(False)

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=lambda _path, office=None, mode="builtin": builtin_result("builtin"),
        cache_factory=FakeCache,
        viewer_factory=label_viewer,
        office=office,
    )
    qtbot.addWidget(window)

    window.open_paths([str(path)])

    qtbot.waitUntil(lambda: "builtin" in page_text(window, 0))
    qtbot.waitUntil(lambda: office.calls == [".docx"])
    assert window.actionOfficePreview.isEnabled() is False
    assert window.actionOfficePreview.toolTip() == "未检测到 Microsoft Office"
    assert office.calls == [".docx"]
    assert office.thread_ids != [threading.get_ident()]


def test_office_action_is_disabled_for_non_office_suffix(qtbot, tmp_path: Path):
    path = tmp_path / "notes.md"
    path.write_text("# notes", encoding="utf-8")
    office = FakeOfficeAvailability(True)

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=lambda _path, office=None, mode="builtin": builtin_result("notes"),
        cache_factory=FakeCache,
        viewer_factory=label_viewer,
        office=office,
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])

    qtbot.waitUntil(lambda: "notes" in page_text(window, 0))
    assert window.actionOfficePreview.isEnabled() is False
    assert office.calls == []


def test_switch_to_office_replaces_viewer_and_status(qtbot, tmp_path: Path):
    path = tmp_path / "doc.docx"
    path.write_bytes(b"x")
    modes: list[str] = []

    def preview_fn(_path: Path, office=None, mode="builtin") -> PreviewResult:
        modes.append(mode)
        if mode == "office":
            return PreviewResult(
                html="<p>office-ready</p>",
                status_label="Office 预览",
                kind="html",
            )
        return builtin_result("builtin-ready")

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=label_viewer,
        office=FakeOfficeAvailability(True),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: "builtin-ready" in page_text(window, 0))
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)

    window.switch_current_tab_to_office()

    qtbot.waitUntil(lambda: "office-ready" in page_text(window, 0))
    assert modes == ["builtin", "office"]
    assert window.status_text() == "Office 预览"
    assert window.actionOfficePreview.isEnabled() is False
    assert window.actionBuiltinPreview.isEnabled() is True


def test_office_failure_keeps_builtin_content_and_result(qtbot, tmp_path: Path):
    path = tmp_path / "doc.docx"
    path.write_bytes(b"x")

    def preview_fn(_path: Path, office=None, mode="builtin") -> PreviewResult:
        if mode == "office":
            raise RuntimeError("COM failed")
        return builtin_result("builtin-stays")

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=label_viewer,
        office=FakeOfficeAvailability(True),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: "builtin-stays" in page_text(window, 0))
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)
    document = next(iter(window._documents.values()))
    builtin = document.last_result

    window.switch_current_tab_to_office()

    qtbot.waitUntil(lambda: "Office 导出失败" in window.status_text())
    assert "builtin-stays" in page_text(window, 0)
    assert document.mode == "builtin"
    assert document.last_result is builtin
    assert window.actionOfficePreview.isEnabled() is True
    assert window.actionBuiltinPreview.isEnabled() is False


def test_switch_back_to_builtin_restores_last_builtin_without_rerender(qtbot, tmp_path: Path):
    path = tmp_path / "sheet.xlsx"
    path.write_bytes(b"x")
    modes: list[str] = []

    def preview_fn(_path: Path, office=None, mode="builtin") -> PreviewResult:
        modes.append(mode)
        if mode == "office":
            return PreviewResult(html="office", status_label="Office 预览")
        return builtin_result("builtin")

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=label_viewer,
        office=FakeOfficeAvailability(True),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: "builtin" in page_text(window, 0))
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)
    window.switch_current_tab_to_office()
    qtbot.waitUntil(lambda: "office" in page_text(window, 0))

    window.switch_current_tab_to_builtin()

    qtbot.waitUntil(lambda: "builtin" in page_text(window, 0))
    assert modes == ["builtin", "office"]
    assert window.status_text() == "内置预览"
    assert next(iter(window._documents.values())).mode == "builtin"


def test_switch_back_preserves_builtin_pdf_and_cleans_both_artifacts(
    qtbot, tmp_path: Path
):
    path = tmp_path / "deck.pptx"
    path.write_bytes(b"pptx")
    builtin_pdf = tmp_path / "builtin.pdf"
    office_pdf = tmp_path / "office.pdf"
    builtin_pdf.write_bytes(b"%PDF builtin")
    office_pdf.write_bytes(b"%PDF office")
    viewed_paths: list[Path] = []

    def preview_fn(_path: Path, office=None, mode="builtin") -> PreviewResult:
        pdf_path = office_pdf if mode == "office" else builtin_pdf
        return PreviewResult(
            html="",
            status_label="Office 预览" if mode == "office" else "内置预览",
            kind="pdf",
            pdf_path=pdf_path,
        )

    def viewer(result: PreviewResult, _source_path: Path) -> QLabel:
        assert result.pdf_path is not None
        assert result.pdf_path.exists()
        viewed_paths.append(result.pdf_path)
        return QLabel(result.status_label)

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=viewer,
        office=FakeOfficeAvailability(True),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: len(viewed_paths) == 1)
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)
    pinned_builtin = viewed_paths[0]

    window.switch_current_tab_to_office()
    qtbot.waitUntil(lambda: len(viewed_paths) == 2)
    pinned_office = viewed_paths[1]
    assert pinned_builtin.exists()
    assert pinned_office.exists()

    window.switch_current_tab_to_builtin()

    qtbot.waitUntil(lambda: len(viewed_paths) == 3)
    assert viewed_paths[2] == pinned_builtin
    assert pinned_builtin.exists()
    assert not pinned_office.exists()

    window.close_tab(0)

    qtbot.waitUntil(lambda: not pinned_builtin.exists())


def test_late_office_result_cannot_overwrite_switched_builtin(qtbot, tmp_path: Path):
    path = tmp_path / "deck.pptx"
    path.write_bytes(b"x")
    office_started = threading.Event()
    release_office = threading.Event()

    def preview_fn(_path: Path, office=None, mode="builtin") -> PreviewResult:
        if mode == "office":
            office_started.set()
            assert release_office.wait(3)
            return PreviewResult(html="LATE OFFICE", status_label="Office 预览")
        return builtin_result("BUILTIN")

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=label_viewer,
        office=FakeOfficeAvailability(True),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: "BUILTIN" in page_text(window, 0))
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)
    window.switch_current_tab_to_office()
    assert office_started.wait(1)

    window.switch_current_tab_to_builtin()
    release_office.set()

    qtbot.waitUntil(lambda: window._executor.active_count() == 0)
    assert "BUILTIN" in page_text(window, 0)
    assert "LATE OFFICE" not in page_text(window, 0)
    assert window.status_text() == "内置预览"


def test_switching_tabs_restores_per_tab_mode_and_status(qtbot, tmp_path: Path):
    first = tmp_path / "first.docx"
    second = tmp_path / "second.docx"
    first.write_bytes(b"1")
    second.write_bytes(b"2")

    def preview_fn(path: Path, office=None, mode="builtin") -> PreviewResult:
        if mode == "office":
            return PreviewResult(html=f"office-{path.name}", status_label="Office 预览")
        return builtin_result(f"builtin-{path.name}")

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=label_viewer,
        office=FakeOfficeAvailability(True),
    )
    qtbot.addWidget(window)
    window.open_paths([str(first), str(second)])
    qtbot.waitUntil(lambda: "builtin-second.docx" in page_text(window, 1))
    window._tabs.setCurrentIndex(0)
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)
    window.switch_current_tab_to_office()
    qtbot.waitUntil(lambda: "office-first.docx" in page_text(window, 0))

    window._tabs.setCurrentIndex(1)

    assert window.status_text() == "内置预览"
    assert window.actionOfficePreview.isEnabled() is True
    assert window.actionBuiltinPreview.isEnabled() is False
    window._tabs.setCurrentIndex(0)
    assert window.status_text() == "Office 预览"
    assert window.actionOfficePreview.isEnabled() is False
    assert window.actionBuiltinPreview.isEnabled() is True


def test_cache_failure_does_not_block_preview(qtbot, tmp_path: Path):
    path = tmp_path / "cache-fault.md"
    path.write_text("x", encoding="utf-8")
    window = make_window(
        lambda _path, office=None, mode="builtin": builtin_result("uncached"),
        FakeCache(fail=True),
    )
    qtbot.addWidget(window)

    window.open_paths([str(path)])

    qtbot.waitUntil(lambda: "uncached" in page_text(window, 0))
    assert "内置预览" in window.status_text()


def test_unsupported_is_nonblocking_and_does_not_add_tab(qtbot, tmp_path: Path):
    path = tmp_path / "x.pdf"
    path.write_bytes(b"%PDF")
    window = make_window(lambda _path, office=None, mode="builtin": builtin_result())
    qtbot.addWidget(window)

    window.open_paths([str(path)])

    assert window.tab_count() == 0
    assert "无法打开" in window.status_text()
    assert "x.pdf" in window.status_text()


def test_plus_action_adds_blank_tab_with_drop_hint(qtbot):
    window = make_window(lambda _path, office=None, mode="builtin": builtin_result())
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
    window = make_window(lambda path, office=None, mode="builtin": builtin_result(path.name))
    qtbot.addWidget(window)
    monkeypatch.setattr(
        "reader.shell.window.QFileDialog.getOpenFileNames",
        lambda *_args, **_kwargs: ([str(first), str(second)], "Documents"),
    )

    window.actionOpen.trigger()

    assert window.tab_count() == 2
    assert window.tab_title(0) == "first.md"
    assert window.tab_title(1) == "second.md"


def test_duplicate_focuses_existing_tab(qtbot, tmp_path: Path):
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("1", encoding="utf-8")
    second.write_text("2", encoding="utf-8")
    window = make_window(lambda path, office=None, mode="builtin": builtin_result(path.name))
    qtbot.addWidget(window)
    window.open_paths([str(first), str(second)])
    qtbot.waitUntil(lambda: "second.md" in page_text(window, 1))

    window.open_paths([str(first)])

    assert window.tab_count() == 2
    assert window.focus_path() == str(first.resolve())


def test_late_result_after_close_cannot_overwrite_shifted_tab(qtbot, tmp_path: Path):
    slow = tmp_path / "slow.md"
    fast = tmp_path / "fast.md"
    slow.write_text("slow", encoding="utf-8")
    fast.write_text("fast", encoding="utf-8")
    release = threading.Event()

    def preview_fn(path: Path, office=None, mode="builtin") -> PreviewResult:
        if path == slow.resolve():
            assert release.wait(3)
            return builtin_result("LATE")
        return builtin_result("FAST")

    window = make_window(preview_fn)
    qtbot.addWidget(window)
    window.open_paths([str(slow), str(fast)])
    qtbot.waitUntil(lambda: "FAST" in page_text(window, 1))
    window.close_tab(0)

    release.set()
    qtbot.waitUntil(lambda: window._executor.active_count() == 0)
    assert window.tab_count() == 1
    assert window.focus_path() == str(fast.resolve())
    assert "FAST" in page_text(window, 0)
    assert "LATE" not in page_text(window, 0)


def test_preview_error_only_changes_its_own_tab(qtbot, tmp_path: Path):
    bad = tmp_path / "bad.md"
    good = tmp_path / "good.md"
    bad.write_text("bad", encoding="utf-8")
    good.write_text("good", encoding="utf-8")

    def preview_fn(path: Path, office=None, mode="builtin") -> PreviewResult:
        if path == bad.resolve():
            raise ValueError("broken parser")
        return builtin_result("GOOD")

    window = make_window(preview_fn)
    qtbot.addWidget(window)
    window.open_paths([str(bad), str(good)])

    qtbot.waitUntil(lambda: "broken parser" in page_text(window, 0))
    qtbot.waitUntil(lambda: "GOOD" in page_text(window, 1))
    assert window.tab_count() == 2


def test_close_last_tab_keeps_visible_empty_window(qtbot, tmp_path: Path):
    path = tmp_path / "one.md"
    path.write_text("one", encoding="utf-8")
    window = make_window(lambda _path, office=None, mode="builtin": builtin_result())
    qtbot.addWidget(window)
    window.show()
    window.open_paths([str(path)])

    window.close_tab(0)

    assert window.tab_count() == 0
    assert window.isVisible()
    assert window.focus_path() is None


def test_new_window_action_and_single_ipc_owner(reader_app):
    app, ipc = reader_app
    first = app.new_window()

    first.actionNewWindow.trigger()

    assert app.window_count() == 2
    assert ipc.become_calls == 1
    assert app.is_primary_instance() is True
    assert first._executor is app._executor
    assert app._windows[-1]._executor is app._executor
    assert app._executor.thread_pool.maxThreadCount() == 1


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

    assert second.geometry().topLeft() == first.geometry().topLeft() + QPoint(32, 32)


def test_new_window_offsets_increment_for_third_window(monkeypatch, qapp):
    from reader.app import ReaderApp
    from reader.shell.window import MainWindow

    base = QPoint(120, 160)

    def fake_center(self, offset: int = 0) -> None:
        self.move(base + QPoint(offset, offset))

    monkeypatch.setattr(MainWindow, "center_on_screen", fake_center)
    app = ReaderApp(qapp, ipc=FakeIpc())
    try:
        first = app.new_window()
        second = app.new_window()
        third = app.new_window()
    finally:
        app.close_all()

    first_top_left = first.geometry().topLeft()
    second_top_left = second.geometry().topLeft()
    third_top_left = third.geometry().topLeft()

    assert first_top_left != second_top_left
    assert second_top_left != third_top_left
    assert first_top_left != third_top_left
    assert second_top_left == first_top_left + QPoint(32, 32)
    assert third_top_left == second_top_left + QPoint(32, 32)


def test_main_window_icon_loading_supports_injected_path(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    missing = tmp_path / "missing.ico"
    loaded: list[object] = []
    window_missing = MainWindow(
        viewer_factory=label_viewer,
        icon_path_provider=lambda: missing,
        icon_applier=loaded.append,
    )
    qtbot.addWidget(window_missing)
    assert loaded == []

    existing = tmp_path / "reader.ico"
    existing.write_bytes(b"not-a-real-ico")
    window_existing = MainWindow(
        viewer_factory=label_viewer,
        icon_path_provider=lambda: existing,
        icon_applier=loaded.append,
    )
    qtbot.addWidget(window_existing)
    assert len(loaded) == 1


def test_reader_app_icon_loading_supports_injected_path(qapp, tmp_path: Path):
    from reader.app import ReaderApp

    loaded: list[object] = []
    missing = tmp_path / "missing.ico"
    app_missing = ReaderApp(
        qapp,
        ipc=FakeIpc(),
        icon_path_provider=lambda: missing,
        icon_applier=loaded.append,
    )
    assert loaded == []

    existing = tmp_path / "reader.ico"
    existing.write_bytes(b"not-a-real-ico")
    app_existing = ReaderApp(
        qapp,
        ipc=FakeIpc(),
        icon_path_provider=lambda: existing,
        icon_applier=loaded.append,
    )
    assert len(loaded) == 1
    app_missing.close_all()
    app_existing.close_all()


def test_shared_executor_delivers_each_result_only_to_owner_window(
    reader_app, qtbot, tmp_path: Path
):
    app, _ipc = reader_app
    first_path = tmp_path / "first.md"
    second_path = tmp_path / "second.pptx"
    first_path.write_text("first", encoding="utf-8")
    second_path.write_bytes(b"pptx")
    source_pdf = tmp_path / "second-source.pdf"
    source_pdf.write_bytes(b"%PDF second")
    first_started = threading.Event()
    release_first = threading.Event()
    pinned: list[Path] = []

    def first_preview(_path: Path, office=None, mode="builtin") -> PreviewResult:
        first_started.set()
        assert release_first.wait(3)
        return builtin_result("WINDOW ONE")

    def second_preview(_path: Path, office=None, mode="builtin") -> PreviewResult:
        return PreviewResult(
            html="",
            status_label="Office 预览",
            kind="pdf",
            pdf_path=source_pdf,
        )

    def second_viewer(result: PreviewResult, _source_path: Path) -> QLabel:
        assert result.pdf_path is not None
        pinned.append(result.pdf_path)
        return QLabel("WINDOW TWO")

    first = app.new_window()
    second = app.new_window()
    first._preview_fn = first_preview
    first._cache_factory = FakeCache
    first._viewer_factory = label_viewer
    second._preview_fn = second_preview
    second._cache_factory = FakeCache
    second._viewer_factory = second_viewer

    first.open_paths([str(first_path)])
    assert first_started.wait(1)
    second.open_paths([str(second_path)])
    assert "正在加载" in page_text(first, 0)
    assert "正在加载" in page_text(second, 0)

    release_first.set()

    qtbot.waitUntil(lambda: "WINDOW ONE" in page_text(first, 0))
    qtbot.waitUntil(lambda: "WINDOW TWO" in page_text(second, 0))
    assert first.tab_title(0) == "first.md"
    assert second.tab_title(0) == "second.pptx"
    assert pinned[0].exists()
    assert pinned[0] != source_pdf


def test_ipc_paths_reuse_latest_window(reader_app, qtbot, tmp_path: Path):
    app, ipc = reader_app
    path = tmp_path / "ipc.md"
    path.write_text("ipc", encoding="utf-8")
    window = app.new_window()
    window._preview_fn = lambda _path, office=None, mode="builtin": builtin_result("IPC")
    window._viewer_factory = label_viewer
    window._cache_factory = FakeCache

    ipc.on_paths([str(path)])

    assert app.window_count() == 1
    assert window.tab_count() == 1
    qtbot.waitUntil(lambda: "IPC" in page_text(window, 0))


def test_closing_last_window_drops_count_and_releases_ipc(reader_app, qtbot):
    from reader.app import ReaderApp

    app, first_ipc = reader_app
    window = app.new_window()

    window.close()

    qtbot.waitUntil(lambda: app.window_count() == 0)
    assert first_ipc.closed is True

    second_ipc = FakeIpc()
    second = ReaderApp(app._qapp, ipc=second_ipc)
    try:
        assert second.is_primary_instance() is True
        assert second_ipc.become_calls == 1
    finally:
        second.close_all()


def test_destroyed_last_window_releases_real_single_instance(
    qapp, qtbot, monkeypatch, tmp_path: Path
):
    import reader.ipc as ipc_module
    from reader.app import ReaderApp

    monkeypatch.setattr(
        ipc_module,
        "SERVER_NAME",
        f"{ipc_module.SERVER_NAME}.window.{uuid.uuid4().hex}",
    )
    monkeypatch.setattr(ipc_module, "LOCK_DIR", tmp_path / "locks")
    first = ReaderApp(qapp)
    second = None
    try:
        assert first.is_primary_instance() is True
        window = first.new_window()
        window.close()
        qtbot.waitUntil(lambda: first.window_count() == 0)

        second = ReaderApp(qapp)
        assert second.is_primary_instance() is True
    finally:
        if second is not None:
            second.close_all()
        first.close_all()


def test_viewer_receives_source_path_and_html_base(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow, _html_base_url

    source = tmp_path / "source" / "page.md"
    source.parent.mkdir()
    source.write_text("body", encoding="utf-8")
    assets = tmp_path / "assets"
    assets.mkdir()
    seen: list[tuple[Path, Path | None]] = []

    def viewer(result: PreviewResult, source_path: Path) -> QLabel:
        seen.append((source_path, result.asset_dir))
        return label_viewer(result)

    result = PreviewResult(
        html="<img src='image.png'>",
        status_label="内置预览",
        asset_dir=assets,
    )
    window = MainWindow(
        preview_fn=lambda _path, office=None, mode="builtin": result,
        cache_factory=FakeCache,
        viewer_factory=viewer,
    )
    qtbot.addWidget(window)
    window.open_paths([str(source)])

    qtbot.waitUntil(lambda: bool(seen))
    assert seen == [(source.resolve(), assets)]
    assert _html_base_url(result, source.resolve()) == QUrl.fromLocalFile(str(assets.resolve()) + "/")
    no_assets = builtin_result()
    assert _html_base_url(no_assets, source.resolve()) == QUrl.fromLocalFile(
        str(source.parent.resolve()) + "/"
    )


def test_pdf_is_pinned_until_tab_closes(qtbot, tmp_path: Path):
    source = tmp_path / "deck.pptx"
    source.write_bytes(b"pptx")
    cached_pdf = tmp_path / "cache-slot" / "preview.pdf"
    cached_pdf.parent.mkdir()
    cached_pdf.write_bytes(b"%PDF pinned")
    cache = FakeCache(
        hit=PreviewResult(
            html="",
            status_label="Office 预览",
            kind="pdf",
            pdf_path=cached_pdf,
        )
    )
    pinned: list[Path] = []

    def viewer(result: PreviewResult, _source_path: Path) -> QLabel:
        assert result.pdf_path is not None
        pinned.append(result.pdf_path)
        return QLabel("PDF")

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=lambda _path, office=None, mode="builtin": pytest.fail("cache hit must skip preview"),
        cache_factory=lambda: cache,
        viewer_factory=viewer,
    )
    qtbot.addWidget(window)
    window.open_paths([str(source)])

    qtbot.waitUntil(lambda: bool(pinned))
    assert pinned[0] != cached_pdf
    assert pinned[0].read_bytes() == b"%PDF pinned"
    cached_pdf.unlink()
    assert pinned[0].exists()

    window.close_tab(0)

    qtbot.waitUntil(lambda: not pinned[0].exists())


def test_pdf_pin_consumes_owned_office_temp_dir(qtbot, tmp_path: Path):
    source = tmp_path / "office.pptx"
    source.write_bytes(b"pptx")
    office_dir = tmp_path / "office-export"
    office_dir.mkdir()
    office_pdf = office_dir / "office.pdf"
    office_pdf.write_bytes(b"%PDF office")
    pinned: list[Path] = []

    def viewer(result: PreviewResult, _source_path: Path) -> QLabel:
        assert result.pdf_path is not None
        pinned.append(result.pdf_path)
        return QLabel("PDF")

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=lambda _path, office=None, mode="builtin": PreviewResult(
            html="",
            status_label="Office 预览",
            kind="pdf",
            asset_dir=office_dir,
            pdf_path=office_pdf,
        ),
        cache_factory=FakeCache,
        viewer_factory=viewer,
    )
    qtbot.addWidget(window)
    window.open_paths([str(source)])

    qtbot.waitUntil(lambda: bool(pinned))
    assert pinned[0].exists()
    assert not office_dir.exists()


def test_failed_pdf_pin_cleans_owned_office_temp_dir(qtbot, tmp_path: Path):
    source = tmp_path / "broken-office.pptx"
    source.write_bytes(b"pptx")
    office_dir = tmp_path / "broken-office-export"
    office_dir.mkdir()
    missing_pdf = office_dir / "missing.pdf"

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=lambda _path, office=None, mode="builtin": PreviewResult(
            html="",
            status_label="Office 预览",
            kind="pdf",
            asset_dir=office_dir,
            pdf_path=missing_pdf,
        ),
        cache_factory=FakeCache,
        viewer_factory=label_viewer,
    )
    qtbot.addWidget(window)
    window.open_paths([str(source)])

    qtbot.waitUntil(lambda: window._executor.active_count() == 0)
    qtbot.waitUntil(lambda: not office_dir.exists())
    assert not office_dir.exists()


def test_window_close_cleans_loaded_pdf_pin(qtbot, tmp_path: Path):
    source = tmp_path / "loaded.pptx"
    source.write_bytes(b"pptx")
    cached_pdf = tmp_path / "cache.pdf"
    cached_pdf.write_bytes(b"%PDF")
    pinned: list[Path] = []

    def viewer(result: PreviewResult, _source_path: Path) -> QLabel:
        assert result.pdf_path is not None
        pinned.append(result.pdf_path)
        return QLabel("PDF")

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=lambda _path, office=None, mode="builtin": pytest.fail("cache hit must skip preview"),
        cache_factory=lambda: FakeCache(
            hit=PreviewResult(
                html="",
                status_label="Office 预览",
                kind="pdf",
                pdf_path=cached_pdf,
            )
        ),
        viewer_factory=viewer,
    )
    window.show()
    window.open_paths([str(source)])
    qtbot.waitUntil(lambda: bool(pinned))
    assert pinned[0].exists()

    window.close()

    qtbot.waitUntil(lambda: not pinned[0].exists())


def test_viewer_reentrancy_close_discards_widget_and_artifact(qtbot, tmp_path: Path):
    source = tmp_path / "close-during-viewer.pptx"
    source.write_bytes(b"pptx")
    pdf = tmp_path / "preview.pdf"
    pdf.write_bytes(b"%PDF")
    cache = FakeCache(
        hit=PreviewResult(html="", status_label="Office 预览", kind="pdf", pdf_path=pdf)
    )
    pinned: list[Path] = []
    window_holder = []

    def closing_viewer(result: PreviewResult, _source_path: Path) -> QLabel:
        assert result.pdf_path is not None
        pinned.append(result.pdf_path)
        window_holder[0].close_tab(0)
        return QLabel("orphan")

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=lambda _path, office=None, mode="builtin": pytest.fail("cache hit must skip preview"),
        cache_factory=lambda: cache,
        viewer_factory=closing_viewer,
    )
    window_holder.append(window)
    qtbot.addWidget(window)
    window.open_paths([str(source)])

    qtbot.waitUntil(lambda: window._executor.active_count() == 0)
    assert window.tab_count() == 0
    assert pinned
    assert not pinned[0].exists()


def test_close_window_while_preview_runs_discards_late_result(qapp, qtbot, tmp_path: Path):
    source = tmp_path / "late.md"
    source.write_text("late", encoding="utf-8")
    started = threading.Event()
    release = threading.Event()
    viewer_calls: list[Path] = []

    def preview_fn(_path: Path, office=None, mode="builtin") -> PreviewResult:
        started.set()
        assert release.wait(3)
        return builtin_result("late")

    def viewer(result: PreviewResult, source_path: Path) -> QLabel:
        viewer_calls.append(source_path)
        return label_viewer(result)

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=viewer,
    )
    executor = window._executor
    registry = qapp._reader_preview_executors
    window.show()
    window.open_paths([str(source)])
    assert started.wait(1)

    window.close()
    release.set()

    qtbot.waitUntil(lambda: executor.active_count() == 0)
    qtbot.waitUntil(lambda: executor not in registry)
    assert viewer_calls == []


def test_error_result_uses_label_without_viewer(qtbot, tmp_path: Path):
    source = tmp_path / "error.md"
    source.write_text("x", encoding="utf-8")
    viewer_called = False

    def viewer(_result: PreviewResult, _source_path: Path) -> QLabel:
        nonlocal viewer_called
        viewer_called = True
        return QLabel()

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=lambda _path, office=None, mode="builtin": PreviewResult(
            html="",
            status_label="预览失败",
            kind="error",
            error="render failed",
        ),
        cache_factory=FakeCache,
        viewer_factory=viewer,
    )
    qtbot.addWidget(window)
    window.open_paths([str(source)])

    qtbot.waitUntil(lambda: "render failed" in page_text(window, 0))
    assert viewer_called is False


def test_missing_worker_output_becomes_target_tab_error(qtbot, tmp_path: Path):
    source = tmp_path / "missing-output.md"
    source.write_text("x", encoding="utf-8")
    started = threading.Event()
    release = threading.Event()

    def blocked_preview(_path: Path, office=None, mode="builtin") -> PreviewResult:
        started.set()
        assert release.wait(3)
        return builtin_result()

    window = make_window(blocked_preview)
    qtbot.addWidget(window)
    window.open_paths([str(source)])
    assert started.wait(1)
    document_id = next(iter(window._documents))
    window._executor._pending[document_id] = (None, None)

    try:
        window._preview_completed(document_id)
        assert "未返回预览结果" in page_text(window, 0)
    finally:
        release.set()
        qtbot.waitUntil(lambda: window._executor.active_count() == 0)


def test_idle_standalone_executor_leaves_qapp_registry(qapp, qtbot):
    from reader.shell.window import MainWindow

    window = MainWindow(viewer_factory=label_viewer)
    executor = window._executor
    registry = qapp._reader_preview_executors
    assert executor in registry
    window.show()

    window.close()

    qtbot.waitUntil(lambda: executor not in registry)


def test_drop_opens_multiple_local_files(qtbot, tmp_path: Path):
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("1", encoding="utf-8")
    second.write_text("2", encoding="utf-8")
    window = make_window(lambda path, office=None, mode="builtin": builtin_result(path.name))
    qtbot.addWidget(window)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(first)), QUrl.fromLocalFile(str(second))])

    class FakeDropEvent:
        def mimeData(self):
            return mime

        def acceptProposedAction(self):
            self.accepted = True

    event = FakeDropEvent()
    window.dropEvent(event)

    assert window.tab_count() == 2
    assert event.accepted is True


def test_drop_on_blank_replaces_first_file_and_appends_extra(qtbot, tmp_path: Path):
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("1", encoding="utf-8")
    second.write_text("2", encoding="utf-8")
    window = make_window(lambda path, office=None, mode="builtin": builtin_result(path.name))
    qtbot.addWidget(window)
    window.add_blank_tab()

    window.open_paths([str(first), str(second)], replace_blank=True)

    assert window.tab_count() == 2
    assert window.tab_title(0) == "first.md"
    assert window.tab_title(1) == "second.md"
    assert "拖入文件" not in page_text(window, 0)


def test_drop_on_current_second_blank_replaces_current_not_first(qtbot, tmp_path: Path):
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("1", encoding="utf-8")
    second.write_text("2", encoding="utf-8")
    window = make_window(lambda path, office=None, mode="builtin": builtin_result(path.name))
    qtbot.addWidget(window)
    window.add_blank_tab()
    window.add_blank_tab()
    assert window.tab_count() == 2
    assert window.tab_title(0) == "未命名"
    assert window.tab_title(1) == "未命名"
    second_blank = window._tabs.widget(1)
    window._tabs.setCurrentIndex(1)

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(first)), QUrl.fromLocalFile(str(second))])

    class FakeDropEvent:
        def mimeData(self):
            return mime

        def acceptProposedAction(self):
            self.accepted = True

    event = FakeDropEvent()
    window.dropEvent(event)

    assert event.accepted is True
    assert window.tab_count() == 3
    assert window.tab_title(0) == "未命名"
    assert window.tab_title(1) == "first.md"
    assert window.tab_title(2) == "second.md"
    assert window._tabs.widget(1) is not second_blank
    assert "拖入文件" in page_text(window, 0)
    assert window.focus_path() == str(second.resolve())
    assert {document.path.name for document in window._documents.values()} == {"first.md", "second.md"}


def test_unsupported_drop_keeps_blank_tab(qtbot, tmp_path: Path):
    unsupported = tmp_path / "bad.pdf"
    unsupported.write_bytes(b"%PDF")
    window = make_window(lambda _path, office=None, mode="builtin": builtin_result())
    qtbot.addWidget(window)
    window.add_blank_tab()

    window.open_paths([str(unsupported)], replace_blank=True)

    assert window.tab_count() == 1
    assert window.tab_title(0) == "未命名"
    assert "无法打开" in window.status_text()


def test_app_user_model_id_is_safe_off_windows(monkeypatch):
    import reader.app as app_module

    monkeypatch.setattr(platform, "system", lambda: "Linux")
    app_module.set_app_user_model_id()


def test_app_user_model_id_uses_reader_desktop_on_windows(monkeypatch):
    import reader.app as app_module

    calls: list[str] = []
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    app_module.set_app_user_model_id(setter=calls.append)

    assert app_module.APP_USER_MODEL_ID == "Reader.Desktop"
    assert calls == ["Reader.Desktop"]
