from __future__ import annotations

import platform
import threading
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtWidgets import QLabel

from reader.preview.result import PreviewResult


class FakeIpc:
    def __init__(self) -> None:
        self.become_calls = 0
        self.closed = False
        self.on_paths = None

    def become_server(self, on_paths):
        self.become_calls += 1
        self.on_paths = on_paths
        return True

    def close(self) -> None:
        self.closed = True


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


def label_viewer(result: PreviewResult) -> QLabel:
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

    def blocked_preview(_path: Path, office=None) -> PreviewResult:
        worker_thread_ids.append(threading.get_ident())
        started.set()
        assert release.wait(3)
        return builtin_result()

    window = make_window(blocked_preview)
    qtbot.addWidget(window)
    before = time.monotonic()
    window.open_paths([str(path)])

    assert time.monotonic() - before < 0.25
    assert window.tab_count() == 1
    assert "正在加载" in page_text(window, 0)
    assert started.wait(1)
    assert worker_thread_ids != [threading.get_ident()]

    release.set()
    qtbot.waitUntil(lambda: "ready" in page_text(window, 0))
    assert "内置预览" in window.status_text()


def test_cache_hit_skips_preview_and_cache_miss_puts(qtbot, tmp_path: Path):
    hit_path = tmp_path / "hit.md"
    miss_path = tmp_path / "miss.md"
    hit_path.write_text("hit", encoding="utf-8")
    miss_path.write_text("miss", encoding="utf-8")
    hit_cache = FakeCache(hit=builtin_result("cached"))
    miss_cache = FakeCache()
    preview_calls: list[Path] = []

    def preview_fn(path: Path, office=None) -> PreviewResult:
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
    assert hit_cache.calls == [("get", hit_path.resolve(), "auto")]
    assert [call[0] for call in miss_cache.calls] == ["get", "put"]


def test_cache_failure_does_not_block_preview(qtbot, tmp_path: Path):
    path = tmp_path / "cache-fault.md"
    path.write_text("x", encoding="utf-8")
    window = make_window(lambda _path, office=None: builtin_result("uncached"), FakeCache(fail=True))
    qtbot.addWidget(window)

    window.open_paths([str(path)])

    qtbot.waitUntil(lambda: "uncached" in page_text(window, 0))
    assert "内置预览" in window.status_text()


def test_unsupported_is_nonblocking_and_does_not_add_tab(qtbot, tmp_path: Path):
    path = tmp_path / "x.pdf"
    path.write_bytes(b"%PDF")
    window = make_window(lambda _path, office=None: builtin_result())
    qtbot.addWidget(window)

    window.open_paths([str(path)])

    assert window.tab_count() == 0
    assert "无法打开" in window.status_text()
    assert "x.pdf" in window.status_text()


def test_duplicate_focuses_existing_tab(qtbot, tmp_path: Path):
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("1", encoding="utf-8")
    second.write_text("2", encoding="utf-8")
    window = make_window(lambda path, office=None: builtin_result(path.name))
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

    def preview_fn(path: Path, office=None) -> PreviewResult:
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
    qtbot.wait(100)
    assert window.tab_count() == 1
    assert window.focus_path() == str(fast.resolve())
    assert "FAST" in page_text(window, 0)
    assert "LATE" not in page_text(window, 0)


def test_preview_error_only_changes_its_own_tab(qtbot, tmp_path: Path):
    bad = tmp_path / "bad.md"
    good = tmp_path / "good.md"
    bad.write_text("bad", encoding="utf-8")
    good.write_text("good", encoding="utf-8")

    def preview_fn(path: Path, office=None) -> PreviewResult:
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
    window = make_window(lambda _path, office=None: builtin_result())
    qtbot.addWidget(window)
    window.show()
    window.open_paths([str(path)])

    window.close_tab(0)

    assert window.tab_count() == 0
    assert window.isVisible()


def test_new_window_action_and_single_ipc_owner(reader_app):
    app, ipc = reader_app
    first = app.new_window()

    first.actionNewWindow.trigger()

    assert app.window_count() == 2
    assert ipc.become_calls == 1


def test_ipc_paths_reuse_latest_window(reader_app, qtbot, tmp_path: Path):
    app, ipc = reader_app
    path = tmp_path / "ipc.md"
    path.write_text("ipc", encoding="utf-8")
    window = app.new_window()
    window._preview_fn = lambda _path, office=None: builtin_result("IPC")
    window._viewer_factory = label_viewer
    window._cache_factory = FakeCache

    ipc.on_paths([str(path)])

    assert app.window_count() == 1
    assert window.tab_count() == 1
    qtbot.waitUntil(lambda: "IPC" in page_text(window, 0))


def test_drop_opens_multiple_local_files(qtbot, tmp_path: Path):
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("1", encoding="utf-8")
    second.write_text("2", encoding="utf-8")
    window = make_window(lambda path, office=None: builtin_result(path.name))
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


def test_app_user_model_id_is_safe_off_windows(monkeypatch):
    import reader.app as app_module

    monkeypatch.setattr(platform, "system", lambda: "Linux")
    app_module.set_app_user_model_id()


def test_app_user_model_id_uses_reader_desktop_on_windows(monkeypatch):
    import reader.app as app_module

    calls: list[str] = []
    shell32 = type(
        "Shell32",
        (),
        {"SetCurrentProcessExplicitAppUserModelID": lambda self, app_id: calls.append(app_id)},
    )()
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(app_module.ctypes, "windll", type("Windll", (), {"shell32": shell32})(), raising=False)

    app_module.set_app_user_model_id()

    assert app_module.APP_USER_MODEL_ID == "Reader.Desktop"
    assert calls == ["Reader.Desktop"]
