from __future__ import annotations

from pathlib import Path

import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent, QUrl
from PySide6.QtWebEngineCore import QWebEngineScript, QWebEngineSettings
from PySide6.QtWidgets import QApplication

from reader.preview.pptx_view import (
    OfflineRequestInterceptor,
    PptxBridge,
    PptxVisualView,
    _install_interceptor,
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


def test_install_interceptor_calls_profile_policy_api():
    calls = []

    class FakeProfile:
        def setUrlRequestInterceptor(self, interceptor):
            calls.append(interceptor)

    marker = object()
    _install_interceptor(FakeProfile(), marker)

    assert calls == [marker]


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
    assert "%23" in view.bridge.sourceUrl
    assert "%25" in view.bridge.sourceUrl
    assert "%E5%AD%A3%E5%BA%A6" in view.bridge.sourceUrl
    assert "%2523" not in view.bridge.sourceUrl
    assert "source" not in view.viewer_url.query().lower()
    view.shutdown()


def test_profile_page_channel_and_webchannel_script_are_isolated(qtbot, tmp_path):
    view = PptxVisualView(_result(), _source(tmp_path, "one.pptx"))
    other = PptxVisualView(_result(), _source(tmp_path, "two.pptx"))
    qtbot.addWidget(view)
    qtbot.addWidget(other)

    settings = view.page().settings()
    assert settings.testAttribute(
        QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls
    )
    assert not settings.testAttribute(
        QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls
    )
    assert view.page().profile() is view.profile
    assert view.page().parent() is view.profile
    assert view.profile is not other.profile
    assert view.profile.isOffTheRecord()
    assert other.profile.isOffTheRecord()
    assert view.profile.parent() is QApplication.instance()
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
    other.shutdown()


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
    page = view.page()
    channel = view.channel
    failures: list[str] = []
    view.render_failed.connect(failures.append)

    view.start()
    view._load_finished(False)
    view._startup_timeout()
    view.bridge.viewerError("renderer parse failed")

    assert failures == ["viewer bundle failed to load"]
    assert fallback_calls[0][0] == "<p>safe fallback</p>"
    assert fallback_calls[0][1].isEmpty()
    assert len(fallback_calls) == 1
    assert view.is_fallback
    assert list(page.scripts().toList()) == []
    assert page.webChannel() is None
    assert "bridge" not in channel.registeredObjects()
    assert not page.settings().testAttribute(
        QWebEngineSettings.WebAttribute.JavascriptEnabled
    )
    view.shutdown()


def test_oversized_fallback_uses_fixed_safe_text(qtbot, tmp_path, monkeypatch):
    result = PreviewResult(
        html="",
        fallback_html="<p>" + ("x" * (2 * 1024 * 1024)) + "</p>",
        status_label="内置预览",
        kind="pptx",
    )
    monkeypatch.setattr(PptxVisualView, "load", lambda *_args: None)
    fallback_calls: list[tuple[str, QUrl]] = []
    monkeypatch.setattr(
        PptxVisualView,
        "setHtml",
        lambda _self, html, base=QUrl(): fallback_calls.append((html, base)),
    )
    view = PptxVisualView(result, _source(tmp_path, "oversized.pptx"))
    qtbot.addWidget(view)

    view.start()
    view._load_finished(False)

    assert len(fallback_calls) == 1
    assert "演示文稿无法进行视觉渲染" in fallback_calls[0][0]
    assert len(fallback_calls[0][0]) < 1024
    assert fallback_calls[0][1].isEmpty()
    view.shutdown()


def test_fallback_disconnects_load_signal_before_stopping(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(PptxVisualView, "load", lambda *_args: None)
    monkeypatch.setattr(PptxVisualView, "setHtml", lambda *_args: None)
    view = PptxVisualView(_result(), _source(tmp_path, "fallback-order.pptx"))
    qtbot.addWidget(view)
    events: list[str] = []
    disconnect = view._disconnect_load_finished
    monkeypatch.setattr(
        view,
        "_disconnect_load_finished",
        lambda: (events.append("disconnect"), disconnect())[1],
    )
    monkeypatch.setattr(view, "stop", lambda: events.append("stop"))

    view.start()
    view._load_finished(False)

    assert events[:2] == ["disconnect", "stop"]
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


def test_load_failure_is_ignored_before_start_and_after_ready(
    qtbot, tmp_path, monkeypatch
):
    monkeypatch.setattr(PptxVisualView, "load", lambda *_args: None)
    monkeypatch.setattr(PptxVisualView, "setHtml", lambda *_args: None)
    view = PptxVisualView(_result(), _source(tmp_path, "load-race.pptx"))
    qtbot.addWidget(view)
    failures: list[str] = []
    view.render_failed.connect(failures.append)

    view._load_finished(False)
    view.start()
    view.bridge.viewerReady(4)
    view._load_finished(False)

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


def test_missing_webchannel_timer_dies_with_view(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(
        PptxVisualView, "_read_webchannel_script", staticmethod(lambda: "")
    )
    failures: list[str] = []
    view = PptxVisualView(_result(), _source(tmp_path, "deleted-qrc.pptx"))
    view.render_failed.connect(failures.append)

    view.deleteLater()
    QCoreApplication.sendPostedEvents(view, QEvent.Type.DeferredDelete)
    QCoreApplication.processEvents()

    assert failures == []


class _FakeRequest:
    def __init__(self, url: str):
        self._url = QUrl(url)
        self.blocked: list[bool] = []

    def requestUrl(self) -> QUrl:
        return self._url

    def block(self, blocked: bool) -> None:
        self.blocked.append(blocked)


def test_interceptor_allows_only_source_bundle_and_non_file_offline_schemes(
    tmp_path,
):
    source = tmp_path / "源 文件 #100%.pptx"
    source.write_bytes(b"x")
    bundle = tmp_path / "assets" / "pptx-viewer"
    bundle_assets = bundle / "assets"
    bundle_assets.mkdir(parents=True)
    index = bundle / "index.html"
    script = bundle_assets / "视图 100%.js"
    style = bundle_assets / "viewer.css"
    index.write_text("index", encoding="utf-8")
    script.write_text("script", encoding="utf-8")
    style.write_text("style", encoding="utf-8")
    sibling = tmp_path / "secret.txt"
    sibling.write_text("secret", encoding="utf-8")
    parent_file = tmp_path.parent / "parent-secret.txt"
    parent_file.write_text("secret", encoding="utf-8")

    interceptor = OfflineRequestInterceptor(source, bundle)
    for path in (source, index, script, style):
        request = _FakeRequest(QUrl.fromLocalFile(str(path)).toString())
        interceptor.interceptRequest(request)
        assert request.blocked == []
    for url in (
        "qrc:/qtwebchannel/qwebchannel.js",
        "data:text/plain,ok",
        "blob:file:///opaque",
    ):
        request = _FakeRequest(url)
        interceptor.interceptRequest(request)
        assert request.blocked == []

    blocked_urls = (
        QUrl.fromLocalFile(str(sibling)).toString(),
        QUrl.fromLocalFile(str(parent_file)).toString(),
        QUrl.fromLocalFile(str(bundle / ".." / ".." / "secret.txt")).toString(),
        "file:///C:/Windows/System32/drivers/etc/hosts",
        "http://example.invalid/a",
        "https://example.invalid/tracker.png",
        "ws://example.invalid/socket",
        "ftp://example.invalid/file",
        "javascript:alert(1)",
    )
    for url in blocked_urls:
        blocked = _FakeRequest(url)
        interceptor.interceptRequest(blocked)
        assert blocked.blocked == [True]

    snapshot = interceptor.blocked_urls()
    assert snapshot == blocked_urls
    assert isinstance(snapshot, tuple)
    interceptor.deleteLater()


def test_interceptor_resolves_symlinks_before_bundle_containment(tmp_path):
    source = _source(tmp_path)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = bundle / "escaped.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        return
    interceptor = OfflineRequestInterceptor(source, bundle)
    request = _FakeRequest(QUrl.fromLocalFile(str(link)).toString())

    interceptor.interceptRequest(request)

    assert request.blocked == [True]
    assert interceptor.blocked_urls() == (request.requestUrl().toString(),)
    interceptor.deleteLater()


def test_shutdown_detaches_in_safe_order_without_javascript_callback(
    qtbot, tmp_path, monkeypatch
):
    view = PptxVisualView(_result(), _source(tmp_path))
    qtbot.addWidget(view)
    old_page = view.page()
    profile = view.profile
    channel = view.channel
    bridge = view.bridge
    events: list[str] = []
    javascript_calls: list[tuple] = []
    monkeypatch.setattr(
        old_page, "runJavaScript", lambda *args: javascript_calls.append(args)
    )
    monkeypatch.setattr(
        profile,
        "setUrlRequestInterceptor",
        lambda interceptor: events.append(f"interceptor:{interceptor is None}"),
    )
    monkeypatch.setattr(
        channel,
        "deregisterObject",
        lambda candidate: events.append(f"deregister:{candidate is bridge}"),
    )
    monkeypatch.setattr(
        old_page,
        "setWebChannel",
        lambda candidate: events.append(f"channel:{candidate is None}"),
    )
    real_set_page = view.setPage

    def record_set_page(page):
        events.append("page")
        real_set_page(page)

    monkeypatch.setattr(view, "setPage", record_set_page)

    view.shutdown()
    inert_page = view.page()
    view.shutdown()

    assert javascript_calls == []
    assert events[:4] == [
        "interceptor:True",
        "deregister:True",
        "channel:True",
        "page",
    ]
    assert inert_page is not old_page
    assert view.profile is None
    assert view.channel is None
    assert view.bridge is None
    assert view.interceptor is None


def test_close_event_performs_explicit_shutdown(qtbot, tmp_path):
    view = PptxVisualView(_result(), _source(tmp_path, "close.pptx"))
    qtbot.addWidget(view)

    view.close()

    assert view.profile is None
    assert view.page().parent() is view


def test_view_deletion_without_shutdown_eventually_releases_profile(qtbot, tmp_path):
    view = PptxVisualView(_result(), _source(tmp_path, "implicit-close.pptx"))
    profile = view.profile
    destroyed: list[bool] = []
    profile.destroyed.connect(lambda: destroyed.append(True))

    view.deleteLater()
    QCoreApplication.sendPostedEvents(view, QEvent.Type.DeferredDelete)
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QCoreApplication.processEvents()

    qtbot.waitUntil(lambda: bool(destroyed))
    assert not shiboken6.isValid(profile)
