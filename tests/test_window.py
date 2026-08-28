from __future__ import annotations

import gc
import json
import platform
import threading
import uuid
import weakref
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QMimeData, QPoint, QThread, QUrl, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QDialog, QLabel, QWidget

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


class BlockingOfficeAvailability(FakeOfficeAvailability):
    def __init__(self, available: bool) -> None:
        super().__init__(available)
        self.started = threading.Event()
        self.release = threading.Event()

    def available_for(self, suffix: str) -> bool:
        self.calls.append(suffix)
        self.thread_ids.append(threading.get_ident())
        self.started.set()
        assert self.release.wait(3)
        return self.available


def label_viewer(result: PreviewResult, _source_path: Path | None = None) -> QLabel:
    label = QLabel(result.error or result.html)
    label.setObjectName("previewContent")
    return label


def builtin_result(text: str = "ready") -> PreviewResult:
    return PreviewResult(html=text, status_label="内置预览")


def visual_result() -> PreviewResult:
    return PreviewResult(
        html="",
        fallback_html="<p>TEXT FALLBACK</p>",
        status_label="内置预览",
        kind="pptx",
    )


def markdown_visual_result() -> PreviewResult:
    return PreviewResult(
        html="",
        fallback_html="<h1>md fallback</h1>",
        status_label="内置预览（视觉模式）",
        kind="markdown",
    )


class FakeVisual(QWidget):
    ready = Signal(int)
    slide_changed = Signal(int)
    render_failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.start_calls = 0
        self.shutdown_calls = 0

    def start(self) -> None:
        self.start_calls += 1

    def shutdown(self) -> None:
        self.shutdown_calls += 1


class ClosingOnStartVisual(FakeVisual):
    def __init__(self, close_callback) -> None:
        super().__init__()
        self._close_callback = close_callback

    def start(self) -> None:
        super().start()
        self._close_callback()


class EmittingOnStartVisual(FakeVisual):
    def start(self) -> None:
        super().start()
        self.ready.emit(6)
        self.render_failed.emit("sync failure")


class FakeMarkdownVisual(FakeVisual):
    open_path = Signal(str)
    missing_link = Signal(str)


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


def preview_content(window, index: int) -> QLabel:
    page = window._tabs.widget(index)
    content = page.findChild(QLabel, "previewContent")
    assert content is not None
    return content


def current_content(window) -> QWidget:
    page = window._tabs.currentWidget()
    assert page is not None
    layout = page.layout()
    assert layout is not None and layout.count() == 1
    content = layout.itemAt(0).widget()
    assert content is not None
    return content


def test_default_viewer_factory_uses_pptx_visual_view(monkeypatch, tmp_path: Path):
    from reader.shell.window import _default_viewer

    source = tmp_path / "deck.pptx"
    source.write_bytes(b"x")
    expected = QWidget()
    calls = []

    def fake_visual(result, path):
        calls.append((result, path))
        return expected

    monkeypatch.setattr("reader.preview.pptx_view.PptxVisualView", fake_visual)

    assert _default_viewer(visual_result(), source) is expected
    assert calls == [(visual_result(), source)]


def test_default_viewer_factory_uses_markdown_visual_view(monkeypatch, tmp_path: Path):
    from reader.shell.window import _default_viewer

    source = tmp_path / "note.md"
    source.write_text("# note", encoding="utf-8")
    expected = QWidget()
    calls = []

    def fake_visual(result, path):
        calls.append((result, path))
        return expected

    monkeypatch.setattr("reader.preview.md_view.MarkdownVisualView", fake_visual)

    assert _default_viewer(markdown_visual_result(), source) is expected
    assert calls == [(markdown_visual_result(), source)]


def test_markdown_default_visual_mode_starts_without_pptx_telemetry(
    qtbot, tmp_path: Path, monkeypatch
):
    from reader.shell.window import MainWindow

    path = tmp_path / "note.md"
    path.write_text("# note", encoding="utf-8")
    visual = FakeMarkdownVisual()
    modes: list[str] = []
    ready_calls: list[tuple[str, int]] = []
    markdown_calls: list[str] = []

    def preview_fn(_path: Path, office=None, mode="builtin") -> PreviewResult:
        modes.append(mode)
        return markdown_visual_result()

    monkeypatch.setattr(
        "reader.shell.window.append_visual_ready",
        lambda source, count: ready_calls.append((source, count)),
    )
    monkeypatch.setattr(
        "reader.shell.window.append_markdown_ready",
        lambda source: markdown_calls.append(source),
    )
    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: visual,
    )
    qtbot.addWidget(window)

    window.open_paths([str(path)])

    qtbot.waitUntil(lambda: visual.start_calls == 1)
    document = next(iter(window._documents.values()))
    assert modes == ["visual"]
    assert document.mode == "visual"
    assert document.builtin_mode == "visual"

    visual.ready.emit(1)
    qtbot.wait(20)
    assert ready_calls == []
    assert markdown_calls == [str(path)]


def test_markdown_wikilink_open_path_opens_tab_and_dedupes_focus(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    source = tmp_path / "source.md"
    sibling = tmp_path / "sibling.md"
    source.write_text("[[sibling]]", encoding="utf-8")
    sibling.write_text("# sibling", encoding="utf-8")
    visuals = iter((FakeMarkdownVisual(), FakeMarkdownVisual()))
    first = None

    def viewer(_result: PreviewResult, _source_path: Path) -> FakeMarkdownVisual:
        nonlocal first
        visual = next(visuals)
        if first is None:
            first = visual
        return visual

    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: markdown_visual_result(),
        cache_factory=FakeCache,
        viewer_factory=viewer,
    )
    qtbot.addWidget(window)
    window.open_paths([str(source)])
    qtbot.waitUntil(lambda: first is not None and first.start_calls == 1)

    first.open_path.emit(str(sibling.resolve()))
    qtbot.waitUntil(lambda: window.tab_count() == 2)
    assert window.focus_path() == str(sibling.resolve())

    window._tabs.setCurrentIndex(0)
    first.open_path.emit(str(sibling.resolve()))
    qtbot.wait(20)
    assert window.tab_count() == 2
    assert window.focus_path() == str(sibling.resolve())


def test_markdown_wikilink_stale_generation_or_closed_signal_is_noop(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    source = tmp_path / "source.md"
    sibling = tmp_path / "sibling.md"
    source.write_text("[[sibling]]", encoding="utf-8")
    sibling.write_text("# sibling", encoding="utf-8")
    first = FakeMarkdownVisual()
    replacement = FakeMarkdownVisual()
    visuals = iter((first, replacement))
    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: markdown_visual_result(),
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: next(visuals),
    )
    qtbot.addWidget(window)
    window.open_paths([str(source)])
    qtbot.waitUntil(lambda: first.start_calls == 1)
    document_id = next(iter(window._documents.keys()))
    document = next(iter(window._documents.values()))
    stale_open_slot = document.visual_connections[3][1]

    window._restart_preview(document_id, "builtin")
    stale_open_slot(str(sibling.resolve()))
    qtbot.waitUntil(lambda: replacement.start_calls == 1)
    qtbot.wait(20)
    assert window.tab_count() == 1
    assert window.focus_path() == str(source.resolve())
    document = next(iter(window._documents.values()))
    closed_open_slot = document.visual_connections[3][1]

    window.close_tab(0)
    closed_open_slot(str(sibling.resolve()))
    qtbot.wait(20)
    assert window.tab_count() == 0


def test_markdown_missing_link_updates_status_without_opening_tab(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    source = tmp_path / "source.md"
    source.write_text("[[missing]]", encoding="utf-8")
    visual = FakeMarkdownVisual()
    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: markdown_visual_result(),
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: visual,
    )
    qtbot.addWidget(window)
    window.open_paths([str(source)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)

    visual.missing_link.emit("missing")
    qtbot.waitUntil(lambda: window.status_text() == "找不到：missing")
    assert window.tab_count() == 1


def test_markdown_close_tab_and_window_call_shutdown(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    first_path = tmp_path / "first.md"
    second_path = tmp_path / "second.md"
    first_path.write_text("# first", encoding="utf-8")
    second_path.write_text("# second", encoding="utf-8")
    first = FakeMarkdownVisual()
    second = FakeMarkdownVisual()
    visuals = iter((first, second))
    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: markdown_visual_result(),
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: next(visuals),
    )
    qtbot.addWidget(window)
    window.open_paths([str(first_path), str(second_path)])
    qtbot.waitUntil(lambda: second.start_calls == 1)

    window.close_tab(0)
    assert first.shutdown_calls == 1
    window.close()
    assert second.shutdown_calls == 1


def test_visual_worker_completion_binds_events_before_start(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    path = tmp_path / "deck.pptx"
    path.write_bytes(b"x")
    visual = FakeVisual()
    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: visual_result(),
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: visual,
        office=FakeOfficeAvailability(False),
    )
    qtbot.addWidget(window)

    window.open_paths([str(path)])

    qtbot.waitUntil(lambda: visual.start_calls == 1)
    visual.ready.emit(7)
    visual.slide_changed.emit(3)
    qtbot.waitUntil(
        lambda: next(iter(window._documents.values())).visual_slide_count == 7
    )
    document = next(iter(window._documents.values()))
    assert document.visual_slide_index == 3
    assert current_content(window) is visual


def test_late_visual_ready_after_close_is_not_logged(
    qtbot, tmp_path: Path, monkeypatch
):
    from reader.shell.window import MainWindow

    path = tmp_path / "late-ready.pptx"
    path.write_bytes(b"x")
    visual = FakeVisual()
    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: visual_result(),
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: visual,
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)
    calls = []
    monkeypatch.setattr(
        "reader.shell.window.append_visual_ready",
        lambda source, count: calls.append((source, count)),
    )

    window.close_tab(0)
    visual.ready.emit(4)
    qtbot.wait(10)

    assert calls == []


def test_current_visual_ready_is_logged_after_state_update(
    qtbot, tmp_path: Path, monkeypatch
):
    from reader.shell.window import MainWindow

    path = tmp_path / "current-ready.pptx"
    path.write_bytes(b"x")
    visual = FakeVisual()
    calls = []
    monkeypatch.setattr(
        "reader.shell.window.append_visual_ready",
        lambda source, count: calls.append((source, count)),
    )
    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: visual_result(),
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: visual,
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)

    visual.ready.emit(4)
    qtbot.waitUntil(lambda: calls == [(str(path), 4)])

    document = next(iter(window._documents.values()))
    assert document.visual_slide_count == 4


def test_visual_render_failure_updates_status_but_keeps_visual_mode(
    qtbot, tmp_path: Path
):
    from reader.shell.window import MainWindow

    path = tmp_path / "fallback.pptx"
    path.write_bytes(b"x")
    visual = FakeVisual()
    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: visual_result(),
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: visual,
        office=FakeOfficeAvailability(False),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)

    visual.render_failed.emit("parse")

    qtbot.waitUntil(
        lambda: window.status_text() == "内置预览（视觉渲染失败）"
    )
    document = next(iter(window._documents.values()))
    assert current_content(window) is visual
    assert document.mode == "visual"
    assert document.builtin_mode == "visual"
    assert document.last_result == visual_result()


def test_manual_text_mode_disposes_visual_and_uses_separate_cache(
    qtbot, tmp_path: Path
):
    from reader.shell.window import MainWindow

    path = tmp_path / "manual.pptx"
    path.write_bytes(b"x")
    visual = FakeVisual()
    cache = FakeCache()
    modes = []

    def preview_fn(_path, office=None, mode="visual"):
        modes.append(mode)
        if mode == "text":
            return PreviewResult(
                html="MANUAL TEXT",
                status_label="内置预览（文本模式）",
                kind="html",
            )
        return visual_result()

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=lambda: cache,
        viewer_factory=lambda result, _path: (
            visual if result.kind == "pptx" else label_viewer(result)
        ),
        office=FakeOfficeAvailability(False),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)
    assert window.actionTextPreview.isEnabled() is True
    assert window.actionVisualPreview.isEnabled() is False

    window.actionTextPreview.trigger()

    qtbot.waitUntil(lambda: "MANUAL TEXT" in page_text(window, 0))
    document = next(iter(window._documents.values()))
    assert visual.shutdown_calls == 1
    assert document.mode == "text"
    assert document.builtin_mode == "text"
    assert modes == ["visual", "text"]
    assert cache.calls == [
        ("get", path.resolve(), "text"),
        ("put", path.resolve(), "text"),
    ]
    assert window.actionTextPreview.isEnabled() is False
    assert window.actionVisualPreview.isEnabled() is True


def test_manual_visual_mode_creates_fresh_bound_visual(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    path = tmp_path / "fresh.pptx"
    path.write_bytes(b"x")
    visuals = [FakeVisual(), FakeVisual()]

    def preview_fn(_path, office=None, mode="visual"):
        if mode == "text":
            return PreviewResult(
                html="TEXT",
                status_label="内置预览（文本模式）",
                kind="html",
            )
        return visual_result()

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=lambda result, _path: (
            visuals.pop(0) if result.kind == "pptx" else label_viewer(result)
        ),
        office=FakeOfficeAvailability(False),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(
        lambda: bool(
            [
                widget
                for widget in window.findChildren(FakeVisual)
                if widget.start_calls == 1
            ]
        )
    )
    first = current_content(window)
    assert isinstance(first, FakeVisual)
    qtbot.waitUntil(lambda: first.start_calls == 1)
    window.actionTextPreview.trigger()
    qtbot.waitUntil(lambda: "TEXT" in page_text(window, 0))

    window.actionVisualPreview.trigger()

    qtbot.waitUntil(lambda: isinstance(current_content(window), FakeVisual))
    second = current_content(window)
    assert isinstance(second, FakeVisual)
    qtbot.waitUntil(lambda: second.start_calls == 1)
    second.ready.emit(5)
    second.slide_changed.emit(2)
    qtbot.waitUntil(
        lambda: next(iter(window._documents.values())).visual_slide_count == 5
    )
    document = next(iter(window._documents.values()))
    assert second is not first
    assert document.visual_slide_index == 2
    assert document.mode == "visual"
    assert document.builtin_mode == "visual"


def test_office_switch_disposes_visual_and_switch_back_starts_fresh_visual(
    qtbot, tmp_path: Path
):
    from reader.shell.window import MainWindow

    path = tmp_path / "office.pptx"
    path.write_bytes(b"x")
    first = FakeVisual()
    restored = FakeVisual()
    visuals = iter((first, restored))

    def preview_fn(_path, office=None, mode="visual"):
        if mode == "office":
            return PreviewResult(html="OFFICE", status_label="Office 预览")
        return visual_result()

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=lambda result, _path: (
            next(visuals) if result.kind == "pptx" else label_viewer(result)
        ),
        office=FakeOfficeAvailability(True),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: first.start_calls == 1)
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)

    window.switch_current_tab_to_office()

    qtbot.waitUntil(lambda: "OFFICE" in page_text(window, 0))
    assert first.shutdown_calls == 1
    window.switch_current_tab_to_builtin()
    qtbot.waitUntil(lambda: restored.start_calls == 1)
    assert current_content(window) is restored
    document = next(iter(window._documents.values()))
    assert document.mode == "visual"
    assert document.builtin_mode == "visual"


def test_office_failure_preserves_current_visual_fallback(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    path = tmp_path / "deck.pptx"
    path.write_bytes(b"x")
    visual = FakeVisual()

    def preview_fn(_path, office=None, mode="visual"):
        if mode == "office":
            raise RuntimeError("COM failed")
        return visual_result()

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=lambda _result, _path: visual,
        office=FakeOfficeAvailability(True),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)
    visual.render_failed.emit("parse")
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)

    window.switch_current_tab_to_office()

    qtbot.waitUntil(lambda: window._executor.active_count() == 0, timeout=10_000)
    document = next(iter(window._documents.values()))
    assert current_content(window) is visual
    assert visual.shutdown_calls == 0
    assert window.status_text() == "内置预览（Office 导出失败）"
    assert document.mode == "visual"
    assert document.builtin_mode == "visual"


def test_pptx_office_probe_starts_only_after_click_and_true_continues_export(
    qtbot, tmp_path: Path
):
    from reader.shell.window import MainWindow

    path = tmp_path / "lazy-office.pptx"
    path.write_bytes(b"x")
    office = FakeOfficeAvailability(True)
    visual = FakeVisual()
    modes: list[str] = []

    def preview_fn(_path, office=None, mode="visual"):
        modes.append(mode)
        if mode == "office":
            return PreviewResult(html="OFFICE READY", status_label="Office 预览")
        return visual_result()

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=lambda result, _path: (
            visual if result.kind == "pptx" else label_viewer(result)
        ),
        office=office,
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)

    assert office.calls == []
    assert modes == ["visual"]
    assert window.actionOfficePreview.isEnabled() is True
    assert (
        window.actionOfficePreview.toolTip()
        == "点击后检测 Microsoft Office"
    )

    window.actionOfficePreview.trigger()

    qtbot.waitUntil(lambda: office.calls == [".pptx"])
    qtbot.waitUntil(lambda: "OFFICE READY" in page_text(window, 0))
    assert modes == ["visual", "office"]


def test_failed_lazy_office_probe_keeps_visual_content(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    path = tmp_path / "missing-office.pptx"
    path.write_bytes(b"x")
    office = FakeOfficeAvailability(False)
    visual = FakeVisual()
    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: visual_result(),
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: visual,
        office=office,
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)

    window.actionOfficePreview.trigger()

    qtbot.waitUntil(
        lambda: window.actionOfficePreview.toolTip()
        == "未检测到 Microsoft Office"
    )
    document = next(iter(window._documents.values()))
    assert office.calls == [".pptx"]
    assert current_content(window) is visual
    assert document.mode == "visual"
    assert document.last_result == visual_result()
    assert window.status_text() == "未检测到 Microsoft Office"


@pytest.mark.parametrize("suffix", [".docx", ".xlsx"])
def test_other_office_formats_also_probe_only_after_click(
    qtbot, tmp_path: Path, suffix: str
):
    from reader.shell.window import MainWindow

    path = tmp_path / f"lazy{suffix}"
    path.write_bytes(b"x")
    office = FakeOfficeAvailability(False)
    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: builtin_result("READY"),
        cache_factory=FakeCache,
        viewer_factory=label_viewer,
        office=office,
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: "READY" in page_text(window, 0))

    assert office.calls == []
    assert window.actionOfficePreview.isEnabled() is True
    window.actionOfficePreview.trigger()
    qtbot.waitUntil(lambda: office.calls == [suffix])


def test_text_and_office_failures_restore_same_visual_widget(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    path = tmp_path / "failure-chain.pptx"
    path.write_bytes(b"x")
    visual = FakeVisual()
    office = FakeOfficeAvailability(True)

    def preview_fn(_path, office=None, mode="visual"):
        if mode == "text":
            raise RuntimeError("text parser failed")
        if mode == "office":
            raise RuntimeError("Office export failed")
        return visual_result()

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: visual,
        office=office,
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)
    original_result = next(iter(window._documents.values())).last_result

    window.actionTextPreview.trigger()
    qtbot.waitUntil(lambda: window._executor.active_count() == 0)

    document = next(iter(window._documents.values()))
    assert current_content(window) is visual
    assert document.mode == "visual"
    assert document.builtin_mode == "visual"
    assert document.last_result is original_result
    assert window.actionVisualPreview.isEnabled() is False
    assert window.actionOfficePreview.isEnabled() is True

    window.actionOfficePreview.trigger()
    qtbot.waitUntil(lambda: window.status_text() == "正在检测 Microsoft Office…")
    qtbot.waitUntil(lambda: window.status_text() == "内置预览（Office 导出失败）")

    assert current_content(window) is visual
    assert document.mode == "visual"
    assert document.last_result is original_result
    assert window.actionVisualPreview.isEnabled() is False


def test_text_failure_from_office_restores_office_mode_and_widget(
    qtbot, tmp_path: Path
):
    from reader.shell.window import MainWindow

    path = tmp_path / "office-text-failure.pptx"
    path.write_bytes(b"x")
    office = FakeOfficeAvailability(True)
    visual = FakeVisual()

    def preview_fn(_path, office=None, mode="visual"):
        if mode == "text":
            raise RuntimeError("text parser failed")
        if mode == "office":
            return PreviewResult(html="OFFICE CURRENT", status_label="Office 预览")
        return visual_result()

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=lambda result, _path: (
            visual if result.kind == "pptx" else label_viewer(result)
        ),
        office=office,
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)
    window.actionOfficePreview.trigger()
    qtbot.waitUntil(lambda: "OFFICE CURRENT" in page_text(window, 0))
    office_widget = current_content(window)

    window.actionTextPreview.trigger()
    qtbot.waitUntil(lambda: window._executor.active_count() == 0)

    document = next(iter(window._documents.values()))
    assert current_content(window) is office_widget
    assert document.mode == "office"
    assert document.builtin_mode == "visual"
    assert window.status_text() == "Office 预览"


def test_repeated_office_failure_replaces_visual_signal_connections(
    qtbot, tmp_path: Path
):
    from reader.shell.window import MainWindow

    path = tmp_path / "repeat-office-failure.pptx"
    path.write_bytes(b"x")
    visual = FakeVisual()

    def preview_fn(_path, office=None, mode="visual"):
        if mode == "office":
            raise RuntimeError("COM failed")
        return visual_result()

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=lambda _result, _path: visual,
        office=FakeOfficeAvailability(True),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)
    document = next(iter(window._documents.values()))
    ready_calls = 0
    failed_calls = 0
    original_ready = window._visual_ready
    original_failed = window._visual_render_failed

    def counted_ready(*args):
        nonlocal ready_calls
        ready_calls += 1
        original_ready(*args)

    def counted_failed(*args):
        nonlocal failed_calls
        failed_calls += 1
        original_failed(*args)

    window._visual_ready = counted_ready
    window._visual_render_failed = counted_failed

    for _attempt in range(3):
        window.switch_current_tab_to_office()
        qtbot.waitUntil(lambda: window._executor.active_count() == 0)
        assert window.status_text() == "内置预览（Office 导出失败）"

    assert len(document.visual_connections) == 3
    visual.ready.emit(9)
    visual.render_failed.emit("current")
    qtbot.wait(10)

    assert ready_calls == 1
    assert failed_calls == 1
    assert document.visual_slide_count == 9
    assert current_content(window) is visual
    assert document.builtin_mode == "visual"
    assert window.status_text() == "内置预览（视觉渲染失败）"


def test_visual_start_sync_signals_update_state_and_actions(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    path = tmp_path / "sync-signals.pptx"
    path.write_bytes(b"x")
    visual = EmittingOnStartVisual()
    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: visual_result(),
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: visual,
        office=FakeOfficeAvailability(False),
    )
    qtbot.addWidget(window)

    window.open_paths([str(path)])

    qtbot.waitUntil(
        lambda: window.status_text() == "内置预览（视觉渲染失败）"
    )
    document = next(iter(window._documents.values()))
    assert document.visual_slide_count == 6
    assert document.mode == "visual"
    assert document.builtin_mode == "visual"
    assert window.actionTextPreview.isEnabled() is True
    assert window.actionVisualPreview.isEnabled() is False


def test_stale_visual_events_after_replacement_are_ignored(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    path = tmp_path / "stale.pptx"
    path.write_bytes(b"x")
    visual = FakeVisual()
    office_started = threading.Event()
    release_office = threading.Event()

    def preview_fn(_path, office=None, mode="visual"):
        if mode == "office":
            office_started.set()
            assert release_office.wait(3)
            return PreviewResult(html="CURRENT OFFICE", status_label="Office 预览")
        return visual_result()

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=lambda result, _path: (
            visual if result.kind == "pptx" else label_viewer(result)
        ),
        office=FakeOfficeAvailability(True),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)
    window.switch_current_tab_to_office()
    qtbot.waitUntil(office_started.is_set)
    document = next(iter(window._documents.values()))
    assert document.visual_slide_count is None
    assert document.visual_slide_index is None

    try:
        visual.ready.emit(99)
        visual.slide_changed.emit(88)
        visual.render_failed.emit("late")
        qtbot.wait(10)

        assert window.status_text() == "正在加载…"
        assert document.mode == "office"
        assert document.builtin_mode == "visual"
        assert document.visual_slide_count is None
        assert document.visual_slide_index is None
    finally:
        release_office.set()
    qtbot.waitUntil(lambda: "CURRENT OFFICE" in page_text(window, 0))
    assert visual.shutdown_calls == 1


def test_close_tab_and_window_shutdown_visuals(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    first_path = tmp_path / "tab.pptx"
    second_path = tmp_path / "window.pptx"
    first_path.write_bytes(b"x")
    second_path.write_bytes(b"x")
    first = FakeVisual()
    second = FakeVisual()
    visuals = iter((first, second))
    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: visual_result(),
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: next(visuals),
        office=FakeOfficeAvailability(False),
    )
    qtbot.addWidget(window)
    window.open_paths([str(first_path), str(second_path)])
    qtbot.waitUntil(lambda: second.start_calls == 1)
    documents = {
        document.path.name: document for document in window._documents.values()
    }

    window.close_tab(0)

    assert first.shutdown_calls == 1
    assert documents[first_path.name].visual_connections == []
    window.close()
    assert second.shutdown_calls == 1
    assert documents[second_path.name].visual_connections == []


def test_late_visual_events_after_window_close_are_ignored(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    path = tmp_path / "closed.pptx"
    path.write_bytes(b"x")
    visual = FakeVisual()
    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: visual_result(),
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: visual,
        office=FakeOfficeAvailability(False),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)

    window.close()
    visual.ready.emit(4)
    visual.slide_changed.emit(2)
    visual.render_failed.emit("late")
    qtbot.wait(10)

    assert visual.shutdown_calls == 1
    assert window.is_closing() is True


@pytest.mark.parametrize("close_target", ["tab", "window"])
def test_visual_start_reentrancy_discards_artifact_without_office_probe(
    qtbot, tmp_path: Path, close_target: str
):
    from reader.shell.window import MainWindow

    path = tmp_path / f"reentrant-{close_target}.docx"
    path.write_bytes(b"x")
    artifact = tmp_path / f"artifact-{close_target}"
    artifact.mkdir()
    (artifact / "image.png").write_bytes(b"image")
    visuals = []
    office = FakeOfficeAvailability(True)
    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: PreviewResult(
            html="<img src='image.png'>",
            status_label="内置预览",
            asset_dir=artifact,
        ),
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: visuals.append(
            ClosingOnStartVisual(
                lambda: (
                    window.close_tab(0)
                    if close_target == "tab"
                    else window.close()
                )
            )
        )
        or visuals[-1],
        office=office,
    )
    executor = window._executor
    documents = window._documents
    availability_requests = window._availability_requests
    if close_target == "tab":
        qtbot.addWidget(window)
    else:
        window.show()

    window.open_paths([str(path)])

    qtbot.waitUntil(lambda: executor.active_count() == 0)
    if close_target == "tab":
        assert window.tab_count() == 0
    assert len(visuals) == 1
    assert visuals[0].start_calls == 1
    assert visuals[0].shutdown_calls == 1
    assert documents == {}
    assert availability_requests == {}
    assert executor._availability_workers == {}
    assert office.calls == []
    assert not artifact.exists()


def test_office_switch_back_restores_manual_text_mode(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    path = tmp_path / "text-office.pptx"
    path.write_bytes(b"x")
    visual = FakeVisual()
    modes = []

    def preview_fn(_path, office=None, mode="visual"):
        modes.append(mode)
        if mode == "text":
            return PreviewResult(
                html="LAST TEXT",
                status_label="内置预览（文本模式）",
            )
        if mode == "office":
            return PreviewResult(html="OFFICE", status_label="Office 预览")
        return visual_result()

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=lambda result, _path: (
            visual if result.kind == "pptx" else label_viewer(result)
        ),
        office=FakeOfficeAvailability(True),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)
    window.actionTextPreview.trigger()
    qtbot.waitUntil(lambda: "LAST TEXT" in page_text(window, 0))
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)

    window.switch_current_tab_to_office()
    qtbot.waitUntil(lambda: "OFFICE" in page_text(window, 0))
    window.switch_current_tab_to_builtin()
    qtbot.waitUntil(lambda: "LAST TEXT" in page_text(window, 0))

    document = next(iter(window._documents.values()))
    assert modes == ["visual", "text", "office"]
    assert document.mode == "text"
    assert document.builtin_mode == "text"
    assert window.status_text() == "内置预览（文本模式）"


def test_office_failure_preserves_manual_text_content(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    path = tmp_path / "text-office-failure.pptx"
    path.write_bytes(b"x")
    visual = FakeVisual()

    def preview_fn(_path, office=None, mode="visual"):
        if mode == "text":
            return PreviewResult(
                html="TEXT STAYS",
                status_label="内置预览（文本模式）",
            )
        if mode == "office":
            raise RuntimeError("COM failed")
        return visual_result()

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=lambda result, _path: (
            visual if result.kind == "pptx" else label_viewer(result)
        ),
        office=FakeOfficeAvailability(True),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)
    window.actionTextPreview.trigger()
    qtbot.waitUntil(lambda: "TEXT STAYS" in page_text(window, 0))
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)
    text_widget = current_content(window)

    window.switch_current_tab_to_office()

    qtbot.waitUntil(
        lambda: window.status_text() == "内置预览（Office 导出失败）"
    )
    document = next(iter(window._documents.values()))
    assert current_content(window) is text_widget
    assert document.mode == "text"
    assert document.builtin_mode == "text"


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


def test_office_probe_uses_pool_independent_from_blocked_preview(
    qapp, qtbot, tmp_path: Path
):
    from reader.shell.window import PreviewExecutor

    path = tmp_path / "blocked.docx"
    path.write_bytes(b"x")
    preview_started = threading.Event()
    release_preview = threading.Event()
    office = BlockingOfficeAvailability(True)
    executor = PreviewExecutor(parent=qapp)
    executor.completed.connect(executor.take_completion)

    def blocked_preview(_path, office=None, mode="builtin"):
        preview_started.set()
        assert release_preview.wait(3)
        return builtin_result()

    executor.submit(
        "preview",
        path,
        blocked_preview,
        office,
        FakeCache,
    )
    assert preview_started.wait(1)
    executor.probe_office("availability", ".docx", office)

    try:
        qtbot.waitUntil(office.started.is_set)
        assert release_preview.is_set() is False
        assert executor.thread_pool is not executor.availability_thread_pool
    finally:
        office.release.set()
        release_preview.set()

    qtbot.waitUntil(lambda: executor.active_count() == 0)
    executor.deleteLater()


def test_cache_hit_skips_preview_and_cache_miss_puts(qtbot, tmp_path: Path):
    hit_path = tmp_path / "hit.docx"
    miss_path = tmp_path / "miss.docx"
    hit_path.write_bytes(b"hit")
    miss_path.write_bytes(b"miss")
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


def test_pptx_visual_skips_cache_and_text_mode_uses_text_cache_strategy(
    qtbot, tmp_path: Path
):
    path = tmp_path / "deck.pptx"
    path.write_bytes(b"x")
    cache = FakeCache()
    modes: list[str] = []

    def preview_fn(_path: Path, office=None, mode="builtin") -> PreviewResult:
        modes.append(mode)
        if mode == "text":
            return PreviewResult(
                html="TEXT",
                status_label="内置预览（文本模式）",
                kind="html",
            )
        return PreviewResult(
            html="VISUAL",
            status_label="内置预览（视觉模式）",
            kind="pptx",
            fallback_html="<p>VISUAL</p>",
        )

    window = make_window(preview_fn, cache)
    qtbot.addWidget(window)

    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: "VISUAL" in page_text(window, 0))
    assert modes == ["visual"]
    assert cache.calls == []

    document_id = next(iter(window._documents))
    window._restart_preview(document_id, "text")
    qtbot.waitUntil(lambda: "TEXT" in page_text(window, 0))
    assert modes == ["visual", "text"]
    assert cache.calls == [
        ("get", path.resolve(), "text"),
        ("put", path.resolve(), "text"),
    ]


def test_markdown_visual_skips_cache_get_and_put(qtbot, tmp_path: Path):
    path = tmp_path / "note.md"
    path.write_text("# Note", encoding="utf-8")
    cache = FakeCache()
    modes: list[str] = []

    def preview_fn(_path: Path, office=None, mode="builtin") -> PreviewResult:
        modes.append(mode)
        return PreviewResult(
            html="",
            status_label="内置预览（视觉模式）",
            kind="markdown",
            fallback_html="<h1>Note</h1>",
        )

    window = make_window(preview_fn, cache)
    qtbot.addWidget(window)

    window.open_paths([str(path)])

    qtbot.waitUntil(lambda: window._executor.active_count() == 0)
    assert modes == ["visual"]
    assert cache.calls == []


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
    assert office.calls == []
    assert window.actionOfficePreview.isEnabled() is True
    assert (
        window.actionOfficePreview.toolTip()
        == "点击后检测 Microsoft Office"
    )
    window.actionOfficePreview.trigger()
    qtbot.waitUntil(
        lambda: window.actionOfficePreview.toolTip()
        == "未检测到 Microsoft Office"
    )
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
    assert (
        window.actionOfficePreview.toolTip()
        != "未检测到 Microsoft Office"
    )
    assert office.calls == []


def test_office_action_shows_neutral_tooltip_while_detecting(qtbot, tmp_path: Path):
    path = tmp_path / "doc.docx"
    path.write_bytes(b"x")
    office = BlockingOfficeAvailability(True)

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
    assert office.calls == []
    window.actionOfficePreview.trigger()

    try:
        qtbot.waitUntil(office.started.is_set)
        assert window.actionOfficePreview.isEnabled() is False
        assert (
            window.actionOfficePreview.toolTip()
            == "正在检测 Microsoft Office…"
        )
        assert window._executor.active_count() == 1
    finally:
        office.release.set()

    qtbot.waitUntil(lambda: window._executor.active_count() == 0, timeout=10_000)
    assert next(iter(window._documents.values())).mode == "office"
    assert window.actionOfficePreview.isEnabled() is False
    assert (
        window.actionOfficePreview.toolTip()
        != "未检测到 Microsoft Office"
    )


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
    assert (
        window.actionOfficePreview.toolTip()
        != "未检测到 Microsoft Office"
    )
    assert window.actionBuiltinPreview.isEnabled() is True

    window.switch_current_tab_to_office()

    qtbot.waitUntil(lambda: window._executor.active_count() == 0)
    assert modes == ["builtin", "office"]


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
    content_before = preview_content(window, 0)
    layout = document.page.layout()
    assert layout is not None
    assert layout.count() == 1

    window.switch_current_tab_to_office()

    qtbot.waitUntil(lambda: "Office 导出失败" in window.status_text())
    assert "builtin-stays" in page_text(window, 0)
    assert preview_content(window, 0) is content_before
    assert layout.count() == 1
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
    path = tmp_path / "deck.docx"
    path.write_bytes(b"docx")
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


def test_office_html_assets_are_pinned_for_viewer_and_cleaned_on_switch_and_close(
    qtbot, tmp_path: Path
):
    path = tmp_path / "document.docx"
    path.write_bytes(b"docx")
    export_dirs: list[Path] = []
    viewer_bases: list[QUrl] = []

    def preview_fn(_path: Path, office=None, mode="builtin") -> PreviewResult:
        if mode == "builtin":
            return builtin_result("BUILTIN")
        export_dir = tmp_path / f"office-html-{len(export_dirs)}"
        resources = export_dir / "document.reader_files"
        resources.mkdir(parents=True)
        (resources / "image.png").write_bytes(b"image")
        export_dirs.append(export_dir)
        return PreviewResult(
            html='<img src="document.reader_files/image.png">',
            status_label="Office 预览",
            kind="html",
            asset_dir=export_dir,
        )

    def viewer(result: PreviewResult, source_path: Path) -> QLabel:
        if result.asset_dir is not None:
            from reader.shell.window import _html_base_url

            viewer_bases.append(_html_base_url(result, source_path))
            assert (result.asset_dir / "document.reader_files" / "image.png").exists()
        return label_viewer(result)

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=viewer,
        office=FakeOfficeAvailability(True),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)

    window.switch_current_tab_to_office()
    qtbot.waitUntil(lambda: len(viewer_bases) == 1)
    first_export = export_dirs[0]
    assert viewer_bases[0] == QUrl.fromLocalFile(str(first_export.resolve()) + "/")
    assert first_export.exists()

    window.switch_current_tab_to_builtin()
    qtbot.waitUntil(lambda: not first_export.exists())

    window.switch_current_tab_to_office()
    qtbot.waitUntil(lambda: len(viewer_bases) == 2)
    second_export = export_dirs[1]
    assert second_export.exists()

    window.close()

    qtbot.waitUntil(lambda: not second_export.exists())


def test_office_html_with_relative_assets_is_not_cached_without_its_directory(
    qtbot, tmp_path: Path
):
    path = tmp_path / "relative.docx"
    path.write_bytes(b"docx")
    export_dir = tmp_path / "relative-export"
    export_dir.mkdir()
    cache = FakeCache()
    result = PreviewResult(
        html='<img src="relative_files/image.png">',
        status_label="Office 预览",
        kind="html",
        asset_dir=export_dir,
    )
    window = make_window(
        lambda _path, office=None, mode="builtin": result,
        cache,
    )
    qtbot.addWidget(window)

    window.open_paths([str(path)])

    qtbot.waitUntil(lambda: window._executor.active_count() == 0)
    assert ("get", path.resolve(), "builtin") in cache.calls
    assert not any(call[0] == "put" for call in cache.calls)


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
    qtbot.waitUntil(office_started.is_set)

    window.switch_current_tab_to_builtin()
    release_office.set()

    qtbot.waitUntil(lambda: window._executor.active_count() == 0)
    assert "BUILTIN" in page_text(window, 0)
    assert "LATE OFFICE" not in page_text(window, 0)
    assert window.status_text() == "内置预览"


def test_close_tab_while_office_worker_runs_discards_and_cleans_result(
    qtbot, tmp_path: Path, monkeypatch
):
    path = tmp_path / "closing-tab.pptx"
    path.write_bytes(b"x")
    office_source_dir = tmp_path / "office-tab-source"
    office_source_dir.mkdir()
    office_pdf = office_source_dir / "office.pdf"
    office_pdf.write_bytes(b"%PDF office")
    pinned_dir = tmp_path / "pinned-tab"
    office_started = threading.Event()
    release_office = threading.Event()
    viewer_calls: list[str] = []

    def preview_fn(_path: Path, office=None, mode="builtin") -> PreviewResult:
        if mode == "office":
            office_started.set()
            assert release_office.wait(3)
            return PreviewResult(
                html="",
                status_label="Office 预览",
                kind="pdf",
                asset_dir=office_source_dir,
                pdf_path=office_pdf,
            )
        return builtin_result("BUILTIN")

    def viewer(result: PreviewResult, _source_path: Path) -> QLabel:
        viewer_calls.append(result.status_label)
        return label_viewer(result)

    monkeypatch.setattr(
        "reader.shell.window.tempfile.mkdtemp",
        lambda **_kwargs: (pinned_dir.mkdir(), str(pinned_dir))[1],
    )
    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=viewer,
        office=FakeOfficeAvailability(True),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)
    window.switch_current_tab_to_office()
    qtbot.waitUntil(office_started.is_set)
    assert (
        window.actionOfficePreview.toolTip()
        != "未检测到 Microsoft Office"
    )

    window.close_tab(0)
    assert window.tab_count() == 0
    release_office.set()

    qtbot.waitUntil(lambda: window._executor.active_count() == 0)
    assert viewer_calls == ["内置预览"]
    assert window._executor._workers == {}
    assert window._executor._pending == {}
    assert not office_source_dir.exists()
    assert not pinned_dir.exists()


def test_close_window_while_office_worker_runs_discards_and_cleans_result(
    qapp, qtbot, tmp_path: Path, monkeypatch
):
    path = tmp_path / "closing-window.xlsx"
    path.write_bytes(b"x")
    office_source_dir = tmp_path / "office-window-source"
    office_source_dir.mkdir()
    office_pdf = office_source_dir / "office.pdf"
    office_pdf.write_bytes(b"%PDF office")
    pinned_dir = tmp_path / "pinned-window"
    office_started = threading.Event()
    release_office = threading.Event()
    viewer_calls: list[str] = []

    def preview_fn(_path: Path, office=None, mode="builtin") -> PreviewResult:
        if mode == "office":
            office_started.set()
            assert release_office.wait(3)
            return PreviewResult(
                html="",
                status_label="Office 预览",
                kind="pdf",
                asset_dir=office_source_dir,
                pdf_path=office_pdf,
            )
        return builtin_result("BUILTIN")

    def viewer(result: PreviewResult, _source_path: Path) -> QLabel:
        viewer_calls.append(result.status_label)
        return label_viewer(result)

    monkeypatch.setattr(
        "reader.shell.window.tempfile.mkdtemp",
        lambda **_kwargs: (pinned_dir.mkdir(), str(pinned_dir))[1],
    )
    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=viewer,
        office=FakeOfficeAvailability(True),
    )
    executor = window._executor
    registry = qapp._reader_preview_executors
    window.show()
    window.open_paths([str(path)])
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)
    window.switch_current_tab_to_office()
    qtbot.waitUntil(office_started.is_set)

    window.close()
    release_office.set()

    qtbot.waitUntil(lambda: executor.active_count() == 0)
    qtbot.waitUntil(lambda: executor not in registry)
    assert viewer_calls == ["内置预览"]
    assert executor._workers == {}
    assert executor._pending == {}
    assert not office_source_dir.exists()
    assert not pinned_dir.exists()


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


def test_restart_cancels_inflight_availability_request(qtbot, tmp_path: Path):
    path = tmp_path / "restart.docx"
    path.write_bytes(b"x")
    office = BlockingOfficeAvailability(True)

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
    window.actionOfficePreview.trigger()
    qtbot.waitUntil(office.started.is_set)
    document_id, document = next(iter(window._documents.items()))
    availability_request_id = document.availability_request_id
    assert availability_request_id is not None

    try:
        window._restart_preview(document_id, "builtin")

        assert availability_request_id not in window._availability_requests
        assert document.availability_request_id is None
        assert availability_request_id in window._executor._cancelled
    finally:
        office.release.set()

    qtbot.waitUntil(lambda: window._executor.active_count() == 0)


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


def test_ux_packaging_regression_multi_open_duplicate_blank_and_office_failure(
    qtbot, tmp_path: Path
):
    first = tmp_path / "first.docx"
    second = tmp_path / "second.md"
    first.write_bytes(b"x")
    second.write_text("second", encoding="utf-8")

    def preview_fn(path: Path, office=None, mode="builtin") -> PreviewResult:
        if mode == "office":
            raise RuntimeError("COM failed")
        return builtin_result(path.name)

    from reader.shell.window import MainWindow

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=label_viewer,
        office=FakeOfficeAvailability(True),
    )
    qtbot.addWidget(window)
    assert window.size().toTuple() == (1200, 800)
    assert window.minimumSize().toTuple() == (800, 500)
    assert window.actionOpen.shortcut().matches(
        QKeySequence(QKeySequence.StandardKey.Open)
    ) == QKeySequence.SequenceMatch.ExactMatch

    window.actionNewTab.trigger()
    window.open_paths([str(first), str(second), str(first)], replace_blank=True)
    qtbot.waitUntil(lambda: window.tab_count() == 2)
    qtbot.waitUntil(lambda: "first.docx" in page_text(window, 0))
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)

    assert window.tab_title(0) == "first.docx"
    assert window.tab_title(1) == "second.md"
    assert window.focus_path() == str(first.resolve())
    window.switch_current_tab_to_office()
    qtbot.waitUntil(lambda: "Office 导出失败" in window.status_text())
    assert "first.docx" in page_text(window, 0)


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


def test_mixed_cross_batch_open_adds_new_tab_then_focuses_existing(
    qtbot, tmp_path: Path
):
    existing = tmp_path / "existing.md"
    new = tmp_path / "new.md"
    existing.write_text("existing", encoding="utf-8")
    new.write_text("new", encoding="utf-8")
    window = make_window(
        lambda path, office=None, mode="builtin": builtin_result(path.name)
    )
    qtbot.addWidget(window)
    window.open_paths([str(existing)])
    qtbot.waitUntil(lambda: "existing.md" in page_text(window, 0))

    window.open_paths([str(existing), str(new)])

    assert window.tab_count() == 2
    assert window.tab_title(1) == "new.md"
    assert window.focus_path() == str(existing.resolve())


def test_duplicate_while_original_is_loading_focuses_original_without_new_tab(
    qtbot, tmp_path: Path
):
    path = tmp_path / "loading.md"
    path.write_text("loading", encoding="utf-8")
    started = threading.Event()
    release = threading.Event()

    def blocked_preview(_path: Path, office=None, mode="builtin") -> PreviewResult:
        started.set()
        assert release.wait(3)
        return builtin_result("loaded")

    window = make_window(blocked_preview)
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    assert started.wait(1)
    original_page = window._tabs.widget(0)

    try:
        window.open_paths([str(path)])
        assert window.tab_count() == 1
        assert window._tabs.widget(0) is original_page
        assert window.focus_path() == str(path.resolve())
    finally:
        release.set()

    qtbot.waitUntil(lambda: "loaded" in page_text(window, 0))


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows path semantics")
def test_duplicate_path_is_case_insensitive_on_windows(qtbot, tmp_path: Path):
    path = tmp_path / "MixedCase.md"
    path.write_text("case", encoding="utf-8")
    window = make_window(
        lambda source, office=None, mode="builtin": builtin_result(source.name)
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: window.tab_count() == 1)

    window.open_paths([str(path).swapcase()])

    assert window.tab_count() == 1
    assert window.focus_path() == str(path.resolve())


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


def test_shared_executor_routes_office_availability_to_owner_windows(
    reader_app, qtbot, tmp_path: Path
):
    app, _ipc = reader_app
    first_path = tmp_path / "first.docx"
    second_path = tmp_path / "second.xlsx"
    first_path.write_bytes(b"docx")
    second_path.write_bytes(b"xlsx")
    first_office = BlockingOfficeAvailability(True)
    second_office = BlockingOfficeAvailability(False)
    first = app.new_window()
    second = app.new_window()
    first._preview_fn = (
        lambda _path, office=None, mode="builtin": builtin_result("FIRST")
    )
    second._preview_fn = (
        lambda _path, office=None, mode="builtin": builtin_result("SECOND")
    )
    first._cache_factory = FakeCache
    second._cache_factory = FakeCache
    first._viewer_factory = label_viewer
    second._viewer_factory = label_viewer
    first._office = first_office
    second._office = second_office

    first.open_paths([str(first_path)])
    second.open_paths([str(second_path)])

    qtbot.waitUntil(lambda: "FIRST" in page_text(first, 0))
    qtbot.waitUntil(lambda: "SECOND" in page_text(second, 0))
    first.actionOfficePreview.trigger()
    second.actionOfficePreview.trigger()
    qtbot.waitUntil(first_office.started.is_set)
    qtbot.waitUntil(
        lambda: all(
            document.availability_request_id is not None
            for window in (first, second)
            for document in window._documents.values()
        )
    )
    first_state = dict(first._availability_requests)
    second_state = dict(second._availability_requests)
    assert first_state
    assert second_state

    app._executor.availability_completed.emit("availability:unknown:999", True)
    qtbot.wait(10)

    assert first._availability_requests == first_state
    assert second._availability_requests == second_state
    first_office.release.set()
    qtbot.waitUntil(second_office.started.is_set)
    second_office.release.set()

    qtbot.waitUntil(lambda: app._executor.active_count() == 0, timeout=10_000)
    qtbot.waitUntil(
        lambda: next(iter(second._documents.values())).office_available is False
    )
    assert (
        second.actionOfficePreview.toolTip()
        == "未检测到 Microsoft Office"
    )
    assert next(iter(first._documents.values())).mode == "office"
    assert first.actionOfficePreview.isEnabled() is False
    assert second.actionOfficePreview.isEnabled() is False
    assert first_office.calls == [".docx"]
    assert second_office.calls == [".xlsx"]


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


def test_ipc_paths_follow_refocused_active_window(reader_app, qapp, qtbot, tmp_path: Path):
    app, ipc = reader_app
    path = tmp_path / "active.md"
    path.write_text("active", encoding="utf-8")
    first = app.new_window()
    second = app.new_window()
    for window in (first, second):
        window._preview_fn = (
            lambda source, office=None, mode="builtin": builtin_result(source.name)
        )
        window._viewer_factory = label_viewer
        window._cache_factory = FakeCache
    first.activateWindow()
    qtbot.waitUntil(lambda: qapp.activeWindow() is first)

    ipc.on_paths([str(path)])

    assert first.tab_count() == 1
    assert second.tab_count() == 0
    qtbot.waitUntil(lambda: "active.md" in page_text(first, 0))


def test_ipc_paths_follow_active_child_dialog_to_parent_window(
    reader_app, qapp, qtbot, tmp_path: Path
):
    app, ipc = reader_app
    path = tmp_path / "dialog-parent.md"
    path.write_text("dialog", encoding="utf-8")
    first = app.new_window()
    second = app.new_window()
    first._preview_fn = (
        lambda source, office=None, mode="builtin": builtin_result(source.name)
    )
    first._viewer_factory = label_viewer
    first._cache_factory = FakeCache
    dialog = QDialog(first)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.activateWindow()
    qtbot.waitUntil(lambda: qapp.activeWindow() is dialog)

    ipc.on_paths([str(path)])

    assert first.tab_count() == 1
    assert second.tab_count() == 0
    qtbot.waitUntil(lambda: "dialog-parent.md" in page_text(first, 0))


def test_ipc_paths_follow_last_activated_window_when_external_app_is_active(
    reader_app, qapp, qtbot, tmp_path: Path, monkeypatch
):
    app, ipc = reader_app
    path = tmp_path / "last-activated.md"
    path.write_text("active history", encoding="utf-8")
    first = app.new_window()
    second = app.new_window()
    for window in (first, second):
        window._preview_fn = (
            lambda source, office=None, mode="builtin": builtin_result(source.name)
        )
        window._viewer_factory = label_viewer
        window._cache_factory = FakeCache
    first.activateWindow()
    qtbot.waitUntil(lambda: qapp.activeWindow() is first)
    qapp.processEvents()
    monkeypatch.setattr(app._qapp, "activeWindow", lambda: None)

    ipc.on_paths([str(path)])

    assert first.tab_count() == 1
    assert second.tab_count() == 0
    qtbot.waitUntil(lambda: "last-activated.md" in page_text(first, 0))


def test_closing_last_activated_window_drops_weak_history_and_routes_to_survivor(
    reader_app, qapp, qtbot, tmp_path: Path, monkeypatch
):
    app, ipc = reader_app
    path = tmp_path / "after-close.md"
    path.write_text("survivor", encoding="utf-8")
    first = app.new_window()
    second = app.new_window()
    second._preview_fn = (
        lambda source, office=None, mode="builtin": builtin_result(source.name)
    )
    second._viewer_factory = label_viewer
    second._cache_factory = FakeCache
    first.activateWindow()
    qtbot.waitUntil(lambda: qapp.activeWindow() is first)
    qapp.processEvents()
    assert app._activation_history
    assert all(isinstance(item, weakref.ReferenceType) for item in app._activation_history)

    first.close()
    first.event(QEvent(QEvent.Type.WindowActivate))
    monkeypatch.setattr(app._qapp, "activeWindow", lambda: None)
    ipc.on_paths([str(path)])

    assert all(item() is not first for item in app._activation_history)
    assert second.tab_count() == 1
    qtbot.waitUntil(lambda: "after-close.md" in page_text(second, 0))


def test_ipc_without_activation_history_falls_back_to_latest_eligible_window(
    reader_app, tmp_path: Path, monkeypatch
):
    app, ipc = reader_app
    path = tmp_path / "fallback.md"
    path.write_text("fallback", encoding="utf-8")
    first = app.new_window()
    second = app.new_window()
    second._preview_fn = (
        lambda source, office=None, mode="builtin": builtin_result(source.name)
    )
    second._viewer_factory = label_viewer
    second._cache_factory = FakeCache
    app._activation_history.clear()
    monkeypatch.setattr(app._qapp, "activeWindow", lambda: None)

    ipc.on_paths([str(path)])

    assert first.tab_count() == 0
    assert second.tab_count() == 1


def test_ipc_callback_opens_all_forwarded_paths(reader_app, qtbot, tmp_path: Path):
    app, ipc = reader_app
    first = tmp_path / "a.md"
    second = tmp_path / "二号.md"
    first.write_text("a", encoding="utf-8")
    second.write_text("b", encoding="utf-8")
    window = app.new_window()
    window._preview_fn = (
        lambda path, office=None, mode="builtin": builtin_result(path.name)
    )
    window._viewer_factory = label_viewer
    window._cache_factory = FakeCache

    ipc.on_paths([str(first), str(second)])

    assert window.tab_count() == 2
    assert window.tab_title(0) == first.name
    assert window.tab_title(1) == second.name
    qtbot.waitUntil(lambda: second.name in page_text(window, 1))


def test_initial_and_ipc_batches_are_logged_separately_before_open(
    reader_app, qtbot, tmp_path: Path, monkeypatch
):
    from reader.smoke import append_smoke_batch

    app, ipc = reader_app
    log_path = tmp_path / "batches.jsonl"
    monkeypatch.setenv("READER_SMOKE_BATCH_LOG", str(log_path))
    initial = [str(tmp_path / "initial-a.md"), str(tmp_path / "initial-b.md")]
    forwarded_paths = [
        tmp_path / "forwarded-a.md",
        tmp_path / "forwarded-b.md",
    ]
    for path in [*(Path(item) for item in initial), *forwarded_paths]:
        path.write_text(path.name, encoding="utf-8")
    append_smoke_batch(initial)
    window = app.new_window()
    window._preview_fn = (
        lambda path, office=None, mode="builtin": builtin_result(path.name)
    )
    window._viewer_factory = label_viewer
    window._cache_factory = FakeCache
    log_seen_at_open: list[list[str]] = []
    real_open_paths = window.open_paths

    def open_after_log(paths, **kwargs):
        log_seen_at_open.extend(
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
        )
        real_open_paths(paths, **kwargs)

    window.open_paths = open_after_log

    ipc.on_paths([str(path) for path in forwarded_paths])

    qtbot.waitUntil(lambda: window.tab_count() == 2)
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == [
        initial,
        [str(path) for path in forwarded_paths],
    ]
    assert log_seen_at_open == [
        initial,
        [str(path) for path in forwarded_paths],
    ]


def test_closing_last_window_drops_count_and_releases_ipc(reader_app, qtbot):
    from reader.app import ReaderApp

    app, first_ipc = reader_app
    window = app.new_window()

    window.close()

    assert window.is_closing() is True
    assert app.window_count() == 0
    assert first_ipc.closed is True

    second_ipc = FakeIpc()
    second = ReaderApp(app._qapp, ipc=second_ipc)
    try:
        assert second.is_primary_instance() is True
        assert second_ipc.become_calls == 1
    finally:
        second.close_all()


def test_closing_window_is_removed_before_ipc_routing(
    reader_app, qapp, qtbot, tmp_path: Path
):
    app, ipc = reader_app
    path = tmp_path / "raced.md"
    path.write_text("race", encoding="utf-8")
    closing = app.new_window()
    survivor = app.new_window()
    survivor._preview_fn = (
        lambda source, office=None, mode="builtin": builtin_result(source.name)
    )
    survivor._viewer_factory = label_viewer
    survivor._cache_factory = FakeCache
    closing.activateWindow()
    qtbot.waitUntil(lambda: qapp.activeWindow() is closing)

    closing.close()
    ipc.on_paths([str(path)])

    assert closing.is_closing() is True
    assert closing.tab_count() == 0
    assert closing._executor._pending == {}
    assert survivor.tab_count() == 1
    qtbot.waitUntil(lambda: "raced.md" in page_text(survivor, 0))


def test_closing_window_open_paths_and_start_preview_are_noops(qtbot, tmp_path: Path):
    path = tmp_path / "ignored.md"
    path.write_text("ignored", encoding="utf-8")
    window = make_window(
        lambda source, office=None, mode="builtin": builtin_result(source.name)
    )
    window.show()
    window.close()

    window.open_paths([str(path)])
    window._start_preview(path.resolve())

    assert window.is_closing() is True
    assert window.tab_count() == 0
    assert window._documents == {}
    assert window._requests == {}
    assert window._owned_request_ids == set()
    assert window._executor.active_count() == 0


def test_destroyed_signal_cannot_drop_a_newer_window(reader_app, qtbot):
    app, _ipc = reader_app
    first = app.new_window()
    survivor = app.new_window()

    first.close()
    replacement = app.new_window()
    qtbot.wait(20)

    assert app.window_count() == 2
    assert any(window is survivor for window in app._windows)
    assert any(window is replacement for window in app._windows)


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
    source = tmp_path / "deck.docx"
    source.write_bytes(b"docx")
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
    source = tmp_path / "loaded.docx"
    source.write_bytes(b"docx")
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
    source = tmp_path / "close-during-viewer.docx"
    source.write_bytes(b"docx")
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
