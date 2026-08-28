from __future__ import annotations

from contextlib import contextmanager
import itertools
import json
import os
from pathlib import Path

import pytest
import shiboken6
from PySide6.QtCore import QEvent, QEventLoop, QLibraryInfo, QTimer, QUrl
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

from reader.preview.md_view import MarkdownVisualView
from reader.preview.result import PreviewResult
from reader.resources import resource_path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "md"
SOURCE = FIXTURE_DIR / "visual-document.md"
LINKED_NOTE = FIXTURE_DIR / "linked-note.md"
OUTBOUND_URLS = (
    "http://example.invalid/pixel.png",
    "https://example.invalid/tracker.png",
    "ws://example.invalid/socket",
    "wss://example.invalid/socket",
)
_js_ids = itertools.count()

qt_root = Path(
    QLibraryInfo.path(QLibraryInfo.LibraryPath.LibraryExecutablesPath)
)
WEBENGINE_MISSING = (
    not resource_path("assets", "md-viewer", "index.html").is_file()
    or not (qt_root / "QtWebEngineProcess.exe").is_file()
)

pytestmark = [
    pytest.mark.webengine,
    pytest.mark.skipif(
        WEBENGINE_MISSING,
        reason="committed WebEngine bundle unavailable",
    ),
]


def _result() -> PreviewResult:
    return PreviewResult(
        html="",
        fallback_html="<p>safe fallback</p>",
        status_label="内置预览（视觉模式）",
        kind="markdown",
    )


def run_js(qtbot, view: QWebEngineView, script: str):
    key = f"js-{next(_js_ids)}"
    completed: dict[str, object] = {}
    view.page().runJavaScript(
        script,
        lambda value, callback_key=key: completed.__setitem__(
            callback_key, value
        ),
    )
    qtbot.waitUntil(lambda: key in completed, timeout=10_000)
    return completed[key]


def run_json(qtbot, view: QWebEngineView, expression: str):
    return json.loads(
        run_js(qtbot, view, f"JSON.stringify({expression})")
    )


@pytest.fixture(scope="session", autouse=True)
def webengine_process_probe(qapp):
    if WEBENGINE_MISSING:
        yield
        return

    view = QWebEngineView()
    loop = QEventLoop()
    outcome: list[bool] = []
    deadline = QTimer()
    deadline.setSingleShot(True)
    deadline.timeout.connect(loop.quit)

    def loaded(succeeded: bool) -> None:
        outcome.append(succeeded)
        loop.quit()

    view.loadFinished.connect(loaded)
    deadline.start(15_000)
    view.load(QUrl("data:text/html,<title>reader-webengine-probe</title>ok"))
    loop.exec()
    deadline.stop()
    final_url = view.url().toString()
    view.stop()
    view.close()
    view.deleteLater()
    qapp.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.processEvents()

    if outcome != [True]:
        pytest.skip(
            "QtWebEngine process cannot start "
            f"(loadFinished={outcome!r}, url={final_url!r})"
        )
    yield


@contextmanager
def _started_real_view(qtbot):
    view = MarkdownVisualView(_result(), SOURCE)
    profile = view.profile
    assert profile is not None
    qtbot.addWidget(view)
    try:
        view.resize(1200, 800)
        view.show()
        ready: list[int] = []
        opened: list[str] = []
        missing: list[str] = []
        failures: list[str] = []
        view.ready.connect(ready.append)
        view.open_path.connect(opened.append)
        view.missing_link.connect(missing.append)
        view.render_failed.connect(failures.append)
        view.start()
        qtbot.waitUntil(lambda: ready == [1], timeout=20_000)
        yield view, opened, missing, failures
    finally:
        view.shutdown()
        qtbot.waitUntil(
            lambda: not shiboken6.isValid(profile), timeout=10_000
        )


def test_real_view_renders_markdown_mermaid_image_and_wikilink_states(qtbot):
    with _started_real_view(qtbot) as (view, opened, missing, failures):
        data = run_json(
            qtbot,
            view,
            """
            (() => {
              const local = Array.from(document.querySelectorAll("img"))
                .find((node) => node.currentSrc.includes("diagram.png"));
              const resolved = document.querySelector(
                'a[data-wiki-target="linked-note"]'
              );
              const unresolved = document.querySelector(
                'a[data-wiki-target="missing-note"]'
              );
              return {
                title: document.querySelector("h1")?.textContent?.trim(),
                table_rows: document.querySelectorAll("table tr").length,
                python_code: Boolean(
                  document.querySelector("pre > code.language-python")
                ),
                mermaid_svg: document.querySelectorAll(
                  ".mermaid-rendered svg"
                ).length,
                mermaid_errors: document.querySelectorAll(
                  ".mermaid-error"
                ).length,
                raw_valid_source_visible: Array.from(
                  document.querySelectorAll("pre > code.language-mermaid")
                ).some((node) =>
                  (node.textContent || "").includes("A[Start] --> B{Check}")
                ),
                local_image_loaded: Boolean(
                  local &&
                  local.complete &&
                  local.naturalWidth > 0 &&
                  local.currentSrc.startsWith("file:")
                ),
                resolved_class: Boolean(
                  resolved?.classList.contains("is-resolved")
                ),
                missing_class: Boolean(
                  unresolved?.classList.contains("is-missing")
                ),
              };
            })()
            """,
        )
        assert data["title"] == "文档地图"
        assert data["table_rows"] >= 2
        assert data["python_code"] is True
        assert data["mermaid_svg"] == 1
        assert data["mermaid_errors"] == 1
        assert data["raw_valid_source_visible"] is False
        assert data["local_image_loaded"] is True
        assert data["resolved_class"] is True
        assert data["missing_class"] is True

        run_js(
            qtbot,
            view,
            """
            (() => {
              document.querySelector('a[data-wiki-target="linked-note"]').click();
              return true;
            })()
            """,
        )
        expected_path = os.path.normcase(os.path.realpath(str(LINKED_NOTE)))
        qtbot.waitUntil(lambda: opened == [expected_path], timeout=10_000)
        assert missing == []

        run_js(
            qtbot,
            view,
            """
            (() => {
              document.querySelector('a[data-wiki-target="missing-note"]').click();
              return true;
            })()
            """,
        )
        qtbot.waitUntil(lambda: missing == ["missing-note"], timeout=10_000)
        assert opened == [expected_path]
        assert failures == []


def test_real_view_blocks_http_https_ws_wss_and_shutdown_invalidates_profile(qtbot):
    with _started_real_view(qtbot) as (view, _opened, _missing, failures):
        interceptor = view.interceptor
        assert interceptor is not None
        assert interceptor.blocked_urls() == ()
        expected_blocked = tuple(
            QUrl(url).toString(QUrl.ComponentFormattingOption.FullyEncoded)
            for url in OUTBOUND_URLS
        )

        view.page().settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )
        run_js(
            qtbot,
            view,
            """
            (() => {
              for (const source of [
                "http://example.invalid/pixel.png",
                "https://example.invalid/tracker.png",
              ]) {
                const image = document.createElement("img");
                image.dataset.outboundProbe = source;
                image.src = source;
                document.body.append(image);
              }
              for (const source of [
                "ws://example.invalid/socket",
                "wss://example.invalid/socket",
              ]) {
                try { new WebSocket(source); } catch {}
              }
              return true;
            })()
            """,
        )
        qtbot.waitUntil(
            lambda: set(expected_blocked).issubset(
                set(interceptor.blocked_urls())
            ),
            timeout=10_000,
        )
        blocked = interceptor.blocked_urls()
        assert len(blocked) == len(expected_blocked)
        assert set(blocked) == set(expected_blocked)
        assert failures == []
