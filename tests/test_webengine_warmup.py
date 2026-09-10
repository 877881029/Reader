from __future__ import annotations

from pathlib import Path

from reader.preview import webengine_warmup


def test_webengine_warmup_is_idempotent(qapp):
    webengine_warmup.reset_warmup_for_tests()
    try:
        assert webengine_warmup.warmup_webengine(qapp) is True
        view = webengine_warmup.kept_view()
        assert view is not None
        assert not view.isVisible()
        assert webengine_warmup.warmup_webengine(qapp) is False
        assert webengine_warmup.kept_view() is view
    finally:
        webengine_warmup.reset_warmup_for_tests()
    assert webengine_warmup.kept_view() is None


def test_warmup_does_not_pump_events_and_skips_when_disabled(monkeypatch, qapp):
    source = Path(webengine_warmup.__file__).read_text(encoding="utf-8")
    assert "processEvents" not in source
    webengine_warmup.reset_warmup_for_tests()
    monkeypatch.setenv("READER_SKIP_WEBENGINE_WARMUP", "1")
    webengine_warmup.schedule_webengine_warmup(qapp, delay_ms=0)
    qapp.processEvents()
    assert webengine_warmup.kept_view() is None
