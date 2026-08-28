from __future__ import annotations

import os
from pathlib import Path

import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent, QUrl
from PySide6.QtWebEngineCore import QWebEngineScript, QWebEngineSettings
from PySide6.QtWidgets import QApplication

from reader.preview.md_view import (
    MarkdownBridge,
    MarkdownVisualView,
    OfflineRequestInterceptor,
    _install_interceptor,
    resolve_wikilink,
)
from reader.preview.result import PreviewResult
from reader.resources import resource_path


def _result() -> PreviewResult:
    return PreviewResult(
        html="",
        fallback_html="<p>markdown fallback</p>",
        status_label="内置预览（视觉模式）",
        kind="markdown",
    )


def _source(tmp_path: Path, name: str = "doc.md") -> Path:
    source = tmp_path / name
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("# source", encoding="utf-8")
    return source


def _touch(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_install_interceptor_calls_profile_policy_api():
    calls = []

    class FakeProfile:
        def setUrlRequestInterceptor(self, interceptor):
            calls.append(interceptor)

    marker = object()
    _install_interceptor(FakeProfile(), marker)

    assert calls == [marker]


def test_resolve_wikilink_accepts_sibling_name_and_md_suffix(tmp_path):
    source = _source(tmp_path, "index.md").resolve()
    sibling = _touch(source.parent / "other.md").resolve()
    explicit = _touch(source.parent / "case-note.MD").resolve()

    assert resolve_wikilink(source, "other") == sibling
    assert resolve_wikilink(source, "other.md") == sibling
    assert resolve_wikilink(source, "case-note.MD") == explicit


def test_resolve_wikilink_rejects_missing_or_invalid_targets(tmp_path):
    source = _source(tmp_path, "root.md").resolve()
    _touch(source.parent / "exists.md")

    absolute = str((tmp_path / "abs.md").resolve())
    invalid_targets = (
        "",
        "   ",
        ".",
        "..",
        "child/note",
        r"child\note",
        "../note",
        r"..\note",
        "/root",
        r"\root",
        "note.txt",
        absolute,
        "missing",
    )
    for target in invalid_targets:
        assert resolve_wikilink(source, target) is None


def test_resolve_wikilink_rejects_symlink_escape_when_available(tmp_path):
    source = _source(tmp_path, "home.md").resolve()
    outside = _touch(tmp_path.parent / "outside.md").resolve()
    escaped = source.parent / "escaped.md"
    try:
        escaped.symlink_to(outside)
    except OSError:
        return

    assert resolve_wikilink(source, "escaped") is None


def test_resolve_wikilink_uses_lexical_source_parent_for_symlink_source(tmp_path):
    lexical_root = tmp_path / "lexical"
    target_root = tmp_path / "target"
    lexical_root.mkdir()
    target_root.mkdir()
    real_source = _touch(target_root / "page.md", "# real")
    source = lexical_root / "page.md"
    try:
        source.symlink_to(real_source)
    except OSError:
        return
    lexical_note = _touch(lexical_root / "note.md", "# local").resolve()
    _touch(target_root / "note.md", "# target sibling")
    outside = _touch(tmp_path / "outside.md", "# outside")
    escaped = lexical_root / "escaped.md"
    try:
        escaped.symlink_to(outside)
    except OSError:
        pass

    assert resolve_wikilink(source, "note") == lexical_note
    assert resolve_wikilink(source, "page") is None
    assert resolve_wikilink(source, "escaped") is None


def test_resolve_wikilink_uses_lexical_parent_when_source_resolve_points_elsewhere(
    tmp_path, monkeypatch
):
    import pathlib

    source = _touch(tmp_path / "lexical" / "source.md", "# source")
    lexical_note = _touch(source.parent / "note.md", "# lexical")
    target_root = _touch(tmp_path / "target" / "source.md", "# target").parent
    _touch(target_root / "note.md", "# target sibling")
    original_resolve = pathlib.Path.resolve

    def fake_resolve(path_obj: pathlib.Path, strict: bool = False):
        if path_obj == source:
            return target_root / "source.md"
        return original_resolve(path_obj, strict=strict)

    monkeypatch.setattr(pathlib.Path, "resolve", fake_resolve)

    assert resolve_wikilink(source, "note") == lexical_note.resolve()


def test_bridge_slot_contract_and_signal_values(tmp_path):
    source = _source(tmp_path, "bridge.md").resolve()
    resolved = _touch(source.parent / "wiki.md").resolve()
    bridge = MarkdownBridge(source)
    ready: list[None] = []
    failed: list[str] = []
    opened: list[str] = []
    missing: list[str] = []
    bridge.ready.connect(lambda: ready.append(None))
    bridge.failed.connect(failed.append)
    bridge.open_path.connect(opened.append)
    bridge.missing.connect(missing.append)

    assert bridge.wikiExists("wiki") is True
    assert bridge.wikiExists("missing") is False
    bridge.openWiki("wiki")
    bridge.openWiki("missing")
    bridge.viewerReady()
    bridge.viewerError("renderer bad path C:/secret/raw.md")

    assert bridge.sourceUrl == QUrl.fromLocalFile(str(source)).toString(
        QUrl.ComponentFormattingOption.FullyEncoded
    )
    assert opened == [os.path.normcase(os.path.realpath(str(resolved)))]
    assert missing == ["missing"]
    assert len(ready) == 1
    assert failed == ["renderer bad path C:/secret/raw.md"]
    bridge.deleteLater()


def test_bridge_missing_payload_is_bounded_to_256_chars(tmp_path):
    bridge = MarkdownBridge(_source(tmp_path, "bound.md").resolve())
    missing: list[str] = []
    bridge.missing.connect(missing.append)
    payload = "x" * 400

    bridge.openWiki(payload)

    assert missing == ["x" * 256]
    bridge.deleteLater()


class _FakeRequest:
    def __init__(self, url: str):
        self._url = QUrl(url)
        self.blocked: list[bool] = []

    def requestUrl(self) -> QUrl:
        return self._url

    def block(self, blocked: bool) -> None:
        self.blocked.append(blocked)


def test_interceptor_allows_source_directory_and_bundle_descendants(tmp_path):
    source = _source(tmp_path, "docs/guide.md").resolve()
    same_dir = _touch(source.parent / "diagram.png")
    child_md = _touch(source.parent / "sub" / "topic.md")
    bundle = tmp_path / "assets" / "md-viewer"
    bundle_asset = _touch(bundle / "assets" / "bundle.js")
    bundle_html = _touch(bundle / "index.html")
    blocked_sibling = _touch(source.parent.parent / "sibling.md")
    blocked_parent = _touch(tmp_path.parent / "parent.md")

    interceptor = OfflineRequestInterceptor(source, bundle)
    for path in (source, same_dir, child_md, bundle_asset, bundle_html):
        request = _FakeRequest(QUrl.fromLocalFile(str(path)).toString())
        interceptor.interceptRequest(request)
        assert request.blocked == []

    blocked_urls = (
        QUrl.fromLocalFile(str(blocked_sibling)).toString(),
        QUrl.fromLocalFile(str(blocked_parent)).toString(),
        "http://example.invalid/a",
        "https://example.invalid/b",
        "ws://example.invalid/s",
        "wss://example.invalid/s",
        "ftp://example.invalid/file",
    )
    for url in blocked_urls:
        request = _FakeRequest(url)
        interceptor.interceptRequest(request)
        assert request.blocked == [True]

    assert interceptor.blocked_urls() == blocked_urls
    interceptor.deleteLater()


def test_interceptor_rejects_symlink_escape_from_allowed_roots(tmp_path):
    source = _source(tmp_path, "src/page.md").resolve()
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    outside = _touch(tmp_path / "outside.png")
    escaped = source.parent / "escaped.png"
    try:
        escaped.symlink_to(outside)
    except OSError:
        return

    interceptor = OfflineRequestInterceptor(source, bundle)
    request = _FakeRequest(QUrl.fromLocalFile(str(escaped)).toString())
    interceptor.interceptRequest(request)

    assert request.blocked == [True]
    assert interceptor.blocked_urls() == (request.requestUrl().toString(),)
    interceptor.deleteLater()


def test_interceptor_uses_lexical_source_root_for_symlink_source(tmp_path):
    lexical_root = tmp_path / "lex-root"
    target_root = tmp_path / "target-root"
    bundle = tmp_path / "bundle"
    lexical_root.mkdir()
    target_root.mkdir()
    bundle.mkdir()
    real_source = _touch(target_root / "doc.md", "# real")
    source = lexical_root / "doc.md"
    try:
        source.symlink_to(real_source)
    except OSError:
        return

    lexical_child = _touch(lexical_root / "image.png")
    target_sibling = _touch(target_root / "sibling.png")
    interceptor = OfflineRequestInterceptor(source, bundle)

    allowed = _FakeRequest(QUrl.fromLocalFile(str(real_source)).toString())
    interceptor.interceptRequest(allowed)
    assert allowed.blocked == []

    allowed_lex = _FakeRequest(QUrl.fromLocalFile(str(lexical_child)).toString())
    interceptor.interceptRequest(allowed_lex)
    assert allowed_lex.blocked == []

    blocked = _FakeRequest(QUrl.fromLocalFile(str(target_sibling)).toString())
    interceptor.interceptRequest(blocked)
    assert blocked.blocked == [True]
    interceptor.deleteLater()


def test_interceptor_uses_lexical_root_when_source_resolve_points_elsewhere(
    tmp_path, monkeypatch
):
    import pathlib

    source = _touch(tmp_path / "lexical" / "doc.md", "# source")
    lexical_child = _touch(source.parent / "inside.png")
    target_root = _touch(tmp_path / "target" / "doc.md", "# target").parent
    target_sibling = _touch(target_root / "sibling.png")
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    original_resolve = pathlib.Path.resolve

    def fake_resolve(path_obj: pathlib.Path, strict: bool = False):
        if path_obj == source:
            return target_root / "doc.md"
        return original_resolve(path_obj, strict=strict)

    monkeypatch.setattr(pathlib.Path, "resolve", fake_resolve)
    interceptor = OfflineRequestInterceptor(source, bundle)

    allowed_lex = _FakeRequest(QUrl.fromLocalFile(str(lexical_child)).toString())
    interceptor.interceptRequest(allowed_lex)
    assert allowed_lex.blocked == []

    blocked_target = _FakeRequest(QUrl.fromLocalFile(str(target_sibling)).toString())
    interceptor.interceptRequest(blocked_target)
    assert blocked_target.blocked == [True]
    interceptor.deleteLater()


def test_interceptor_allows_qrc_data_blob_schemes(tmp_path):
    source = _source(tmp_path, "docs/guide.md").resolve()
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    interceptor = OfflineRequestInterceptor(source, bundle)
    for url in (
        "qrc:/qtwebchannel/qwebchannel.js",
        "data:text/plain,ok",
        "blob:file:///opaque",
    ):
        request = _FakeRequest(url)
        interceptor.interceptRequest(request)
        assert request.blocked == []
    interceptor.deleteLater()


def test_interceptor_blocks_commonpath_prefix_collision(tmp_path):
    source = _source(tmp_path, "docs/page.md").resolve()
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    outside_prefix = _touch(tmp_path / "docs-evil" / "steal.png")
    interceptor = OfflineRequestInterceptor(source, bundle)
    request = _FakeRequest(QUrl.fromLocalFile(str(outside_prefix)).toString())

    interceptor.interceptRequest(request)

    assert request.blocked == [True]
    interceptor.deleteLater()


def test_constructor_does_not_load_and_creates_isolated_webengine_context(
    qtbot, tmp_path, monkeypatch
):
    loads: list[QUrl] = []
    monkeypatch.setattr(MarkdownVisualView, "load", lambda _self, url: loads.append(url))

    source = _source(tmp_path, "季度 #1 100%.md").resolve()
    view = MarkdownVisualView(_result(), source)
    other = MarkdownVisualView(_result(), _source(tmp_path, "second.md").resolve())
    qtbot.addWidget(view)
    qtbot.addWidget(other)

    assert loads == []
    assert view.started is False
    assert view.profile is not other.profile
    assert view.profile.isOffTheRecord()
    assert view.page().profile() is view.profile
    assert view.page().parent() is view.profile
    assert view.channel.registeredObjects()["bridge"] is view.bridge
    assert view.bridge.sourceUrl == QUrl.fromLocalFile(str(source)).toString(
        QUrl.ComponentFormattingOption.FullyEncoded
    )
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


def test_start_loads_md_bundle_once_and_readiness_emits_one(qtbot, tmp_path, monkeypatch):
    loads: list[QUrl] = []
    monkeypatch.setattr(MarkdownVisualView, "load", lambda _self, url: loads.append(url))
    view = MarkdownVisualView(_result(), _source(tmp_path).resolve())
    qtbot.addWidget(view)
    ready_counts: list[int] = []
    view.ready.connect(ready_counts.append)

    view.start()
    view.start()
    view.bridge.viewerReady()
    view.bridge.viewerReady()

    bundle = resource_path("assets", "md-viewer", "index.html").resolve()
    assert loads == [QUrl.fromLocalFile(str(bundle))]
    assert view.startup_timer.interval() == 15_000
    assert view.started is True
    assert ready_counts == [1]
    view.shutdown()


def test_fallback_is_safe_and_atomic_for_load_timeout_and_bridge_error(
    qtbot, tmp_path, monkeypatch
):
    monkeypatch.setattr(MarkdownVisualView, "load", lambda *_args: None)
    fallback_calls: list[tuple[str, QUrl]] = []
    monkeypatch.setattr(
        MarkdownVisualView,
        "setHtml",
        lambda _self, html, base=QUrl(): fallback_calls.append((html, base)),
    )
    view = MarkdownVisualView(_result(), _source(tmp_path, "fallback.md").resolve())
    qtbot.addWidget(view)
    page = view.page()
    channel = view.channel
    failures: list[str] = []
    view.render_failed.connect(failures.append)

    view.start()
    view._load_finished(False)
    view._startup_timeout()
    view.bridge.viewerError("raw traceback C:/private/secret.md")

    assert len(fallback_calls) == 1
    assert fallback_calls[0][0] == "<p>markdown fallback</p>"
    assert fallback_calls[0][1].isEmpty()
    assert list(page.scripts().toList()) == []
    assert page.webChannel() is None
    assert "bridge" not in channel.registeredObjects()
    assert not page.settings().testAttribute(
        QWebEngineSettings.WebAttribute.JavascriptEnabled
    )
    assert failures == ["Markdown 视觉预览不可用，请切换文本模式重试。"]
    view.shutdown()


def test_fallback_keeps_interceptor_until_shutdown(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(MarkdownVisualView, "load", lambda *_args: None)
    source = _source(tmp_path, "docs/source.md").resolve()
    outside = _touch(tmp_path / "outside.png")
    source_image = _touch(source.parent / "inside.png")
    result = PreviewResult(
        html="",
        fallback_html=f"<img src='{outside.as_uri()}'><img src='{source_image.as_uri()}'>",
        status_label="内置预览",
        kind="markdown",
    )
    view = MarkdownVisualView(result, source)
    qtbot.addWidget(view)
    detach_calls: list[object | None] = []
    monkeypatch.setattr(
        view.profile, "setUrlRequestInterceptor", lambda value: detach_calls.append(value)
    )

    view.start()
    view._load_finished(False)
    assert view.is_fallback
    assert view.interceptor is not None
    assert detach_calls == []

    blocked = _FakeRequest(QUrl.fromLocalFile(str(outside)).toString())
    view.interceptor.interceptRequest(blocked)
    assert blocked.blocked == [True]

    allowed = _FakeRequest(QUrl.fromLocalFile(str(source_image)).toString())
    view.interceptor.interceptRequest(allowed)
    assert allowed.blocked == []

    view.shutdown()
    assert detach_calls == [None]
    assert view.interceptor is None


def test_oversized_fallback_uses_fixed_safe_text(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(MarkdownVisualView, "load", lambda *_args: None)
    result = PreviewResult(
        html="",
        fallback_html="<p>" + ("x" * (2 * 1024 * 1024)) + "</p>",
        status_label="内置预览",
        kind="markdown",
    )
    fallback_calls: list[tuple[str, QUrl]] = []
    monkeypatch.setattr(
        MarkdownVisualView,
        "setHtml",
        lambda _self, html, base=QUrl(): fallback_calls.append((html, base)),
    )
    view = MarkdownVisualView(result, _source(tmp_path, "oversized.md").resolve())
    qtbot.addWidget(view)

    view.start()
    view._load_finished(False)

    assert len(fallback_calls) == 1
    assert "Markdown 文档无法进行视觉渲染" in fallback_calls[0][0]
    assert len(fallback_calls[0][0]) < 1024
    assert fallback_calls[0][1].isEmpty()
    view.shutdown()


def test_missing_webchannel_resource_triggers_safe_fallback(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(
        MarkdownVisualView, "_read_webchannel_script", staticmethod(lambda: "")
    )
    monkeypatch.setattr(MarkdownVisualView, "setHtml", lambda *_args: None)
    view = MarkdownVisualView(_result(), _source(tmp_path, "missing-qrc.md").resolve())
    qtbot.addWidget(view)
    failures: list[str] = []
    view.render_failed.connect(failures.append)

    view.start()
    qtbot.waitUntil(lambda: bool(failures))

    assert view.started is False
    assert view.is_fallback
    assert failures == ["Markdown 视觉预览不可用，请切换文本模式重试。"]
    view.shutdown()


def test_shutdown_idempotent_and_late_bridge_calls_have_no_effect(
    qtbot, tmp_path, monkeypatch
):
    monkeypatch.setattr(MarkdownVisualView, "load", lambda *_args: None)
    view = MarkdownVisualView(_result(), _source(tmp_path, "shutdown.md").resolve())
    qtbot.addWidget(view)
    bridge = view.bridge
    opened: list[str] = []
    missing: list[str] = []
    ready: list[int] = []
    failed: list[str] = []
    view.open_path.connect(opened.append)
    view.missing_link.connect(missing.append)
    view.ready.connect(ready.append)
    view.render_failed.connect(failed.append)

    view.shutdown()
    view.shutdown()
    bridge.viewerReady()
    bridge.openWiki("missing")
    bridge.viewerError("late error")

    assert opened == []
    assert missing == []
    assert ready == []
    assert failed == []
    assert view.profile is None
    assert view.channel is None
    assert view.bridge is None
    assert view.interceptor is None


def test_close_during_start_is_safe(qtbot, tmp_path, monkeypatch):
    def close_on_load(self, _url):
        self.close()

    monkeypatch.setattr(MarkdownVisualView, "load", close_on_load)
    view = MarkdownVisualView(_result(), _source(tmp_path, "close-start.md").resolve())
    qtbot.addWidget(view)

    view.start()

    assert view.profile is None
    assert view.page().parent() is view


def test_view_delete_without_shutdown_releases_profile(qtbot, tmp_path):
    view = MarkdownVisualView(_result(), _source(tmp_path, "implicit.md").resolve())
    profile = view.profile
    destroyed: list[bool] = []
    profile.destroyed.connect(lambda: destroyed.append(True))

    view.deleteLater()
    QCoreApplication.sendPostedEvents(view, QEvent.Type.DeferredDelete)
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QCoreApplication.processEvents()

    qtbot.waitUntil(lambda: bool(destroyed))
    assert not shiboken6.isValid(profile)

