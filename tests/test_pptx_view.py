from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEngineScript, QWebEngineSettings

from reader.preview.pptx_view import (
    OfflineRequestInterceptor,
    PptxBridge,
    PptxVisualView,
)
from reader.preview.result import PreviewResult
from reader.resources import resource_path


def _result() -> PreviewResult:
    return PreviewResult(
        html="",
        fallback_html="<p>safe fallback</p>",
        status_label="内置预览",
        kind="pptx",
    )


def _source(tmp_path: Path, name: str = "deck.pptx") -> Path:
    source = tmp_path / name
    source.write_bytes(b"x")
    return source


def test_constructor_does_not_load_and_source_is_once_encoded(
    qtbot, tmp_path, monkeypatch
):
    loads: list[QUrl] = []
    monkeypatch.setattr(PptxVisualView, "load", lambda _self, url: loads.append(url))
    source = _source(tmp_path, "季度 #1 100%.pptx")

    view = PptxVisualView(_result(), source)
    qtbot.addWidget(view)

    assert loads == []
    assert view.started is False
    assert view.bridge.sourceUrl == QUrl.fromLocalFile(
        str(source.resolve())
    ).toString(QUrl.ComponentFormattingOption.FullyEncoded)
    assert "%2523" not in view.bridge.sourceUrl
    assert "source" not in view.viewer_url.query().lower()
    view.shutdown()


def test_profile_page_channel_and_webchannel_script_are_isolated(qtbot, tmp_path):
    view = PptxVisualView(_result(), _source(tmp_path))
    qtbot.addWidget(view)

    settings = view.page().settings()
    assert settings.testAttribute(
        QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls
    )
    assert not settings.testAttribute(
        QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls
    )
    assert view.page().profile() is view.profile
    assert view.page().webChannel() is view.channel
    assert view.channel.registeredObjects()["bridge"] is view.bridge
    scripts = list(view.page().scripts().toList())
    injected = [script for script in scripts if script.name() == "reader-qwebchannel"]
    assert len(injected) == 1
    assert "QWebChannel" in injected[0].sourceCode()
    assert (
        injected[0].injectionPoint()
        == QWebEngineScript.InjectionPoint.DocumentCreation
    )
    assert injected[0].worldId() == QWebEngineScript.ScriptWorldId.MainWorld
    assert not injected[0].runsOnSubFrames()
    view.shutdown()


def test_start_loads_bundle_once_and_arms_fifteen_second_timer(
    qtbot, tmp_path, monkeypatch
):
    loads: list[QUrl] = []
    monkeypatch.setattr(PptxVisualView, "load", lambda _self, url: loads.append(url))
    view = PptxVisualView(_result(), _source(tmp_path))
    qtbot.addWidget(view)

    view.start()
    view.start()

    assert view.started is True
    assert view.startup_timer.interval() == 15_000
    assert view.startup_timer.isSingleShot()
    assert view.startup_timer.isActive()
    bundle = resource_path("assets", "pptx-viewer", "index.html").resolve()
    assert loads == [QUrl.fromLocalFile(str(bundle))]
    assert loads[0].query() == ""
    view.shutdown()


def test_start_failure_timeout_and_bridge_error_fallback_only_once(
    qtbot, tmp_path, monkeypatch
):
    monkeypatch.setattr(PptxVisualView, "load", lambda *_args: None)
    fallback_calls: list[tuple[str, QUrl]] = []
    monkeypatch.setattr(
        PptxVisualView,
        "setHtml",
        lambda _self, html, base=QUrl(): fallback_calls.append((html, base)),
    )
    view = PptxVisualView(_result(), _source(tmp_path))
    qtbot.addWidget(view)
    failures: list[str] = []
    view.render_failed.connect(failures.append)

    view.start()
    view._load_finished(False)
    view._startup_timeout()
    view.bridge.viewerError("renderer parse failed")

    assert failures == ["viewer bundle failed to load"]
    assert fallback_calls[0][0] == "<p>safe fallback</p>"
    assert len(fallback_calls) == 1
    assert view.is_fallback
    view.shutdown()


def test_ready_and_slide_signals_relay_from_complete_bridge(qtbot, tmp_path):
    bridge = PptxBridge(_source(tmp_path), test_fail_slide=2)
    ready: list[int] = []
    failed: list[str] = []
    changed: list[int] = []
    bridge.ready.connect(ready.append)
    bridge.failed.connect(failed.append)
    bridge.changed.connect(changed.append)

    bridge.viewerReady(4)
    bridge.viewerError("bad deck")
    bridge.slideChanged(1)

    assert bridge.testFailSlide == 2
    assert ready == [4]
    assert failed == ["bad deck"]
    assert changed == [1]
    bridge.deleteLater()

    view = PptxVisualView(_result(), _source(tmp_path, "signals.pptx"))
    qtbot.addWidget(view)
    view_ready: list[int] = []
    view_slides: list[int] = []
    view.ready.connect(view_ready.append)
    view.slide_changed.connect(view_slides.append)
    view.bridge.viewerReady(3)
    view.bridge.slideChanged(2)
    assert view_ready == [3]
    assert view_slides == [2]
    assert not view.startup_timer.isActive()
    view.shutdown()


def test_queued_startup_timeout_after_ready_is_ignored(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(PptxVisualView, "load", lambda *_args: None)
    monkeypatch.setattr(PptxVisualView, "setHtml", lambda *_args: None)
    view = PptxVisualView(_result(), _source(tmp_path, "ready-race.pptx"))
    qtbot.addWidget(view)
    failures: list[str] = []
    ready: list[int] = []
    view.render_failed.connect(failures.append)
    view.ready.connect(ready.append)

    view.start()
    view.bridge.viewerReady(4)
    view._startup_timeout()

    assert ready == [4]
    assert failures == []
    assert not view.is_fallback
    view.shutdown()


def test_missing_webchannel_resource_queues_safe_fallback(
    qtbot, tmp_path, monkeypatch
):
    monkeypatch.setattr(
        PptxVisualView, "_read_webchannel_script", staticmethod(lambda: "")
    )
    monkeypatch.setattr(PptxVisualView, "setHtml", lambda *_args: None)
    view = PptxVisualView(_result(), _source(tmp_path, "missing-qrc.pptx"))
    qtbot.addWidget(view)
    failures: list[str] = []
    view.render_failed.connect(failures.append)

    view.start()
    qtbot.waitUntil(lambda: bool(failures))

    assert view.started is False
    assert view.is_fallback
    assert failures == ["Qt WebChannel script unavailable"]
    view.shutdown()


class _FakeRequest:
    def __init__(self, url: str):
        self._url = QUrl(url)
        self.blocked: list[bool] = []

    def requestUrl(self) -> QUrl:
        return self._url

    def block(self, blocked: bool) -> None:
        self.blocked.append(blocked)


def test_interceptor_allows_offline_schemes_and_snapshots_blocked_urls():
    interceptor = OfflineRequestInterceptor()
    for url in (
        "file:///C:/deck.pptx",
        "qrc:/qtwebchannel/qwebchannel.js",
        "data:text/plain,ok",
        "blob:file:///opaque",
    ):
        request = _FakeRequest(url)
        interceptor.interceptRequest(request)
        assert request.blocked == []

    blocked = _FakeRequest("https://example.invalid/tracker.png")
    interceptor.interceptRequest(blocked)

    assert blocked.blocked == [True]
    snapshot = interceptor.blocked_urls()
    assert snapshot == ("https://example.invalid/tracker.png",)
    assert isinstance(snapshot, tuple)
    interceptor.deleteLater()


def test_shutdown_calls_dispose_detaches_owned_objects_and_is_idempotent(
    qtbot, tmp_path, monkeypatch
):
    view = PptxVisualView(_result(), _source(tmp_path))
    qtbot.addWidget(view)
    old_page = view.page()
    scripts: list[str] = []
    monkeypatch.setattr(old_page, "runJavaScript", lambda script: scripts.append(script))

    view.shutdown()
    inert_page = view.page()
    view.shutdown()

    assert scripts == [
        "if (typeof window.readerPptxDispose === 'function') "
        "{ window.readerPptxDispose(); }"
    ]
    assert inert_page is not old_page
    assert view.profile is None
    assert view.channel is None
    assert view.bridge is None
    assert view.interceptor is None
