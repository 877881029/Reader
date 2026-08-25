from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_visual_ready_log_is_disabled_without_environment(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("READER_SMOKE_VISUAL_LOG", raising=False)
    from reader.smoke import append_visual_ready

    assert append_visual_ready("C:/docs/deck.pptx", 4) is False
    assert list(tmp_path.iterdir()) == []


def test_visual_ready_flushes_and_fsyncs(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "visual.jsonl"
    monkeypatch.setenv("READER_SMOKE_VISUAL_LOG", str(log_path))
    fsync_calls: list[int] = []
    monkeypatch.setattr("reader.smoke.os.fsync", fsync_calls.append)
    from reader.smoke import append_visual_ready

    assert append_visual_ready("C:/文档/deck.pptx", 4) is True

    assert json.loads(log_path.read_text(encoding="utf-8")) == {
        "path": "C:/文档/deck.pptx",
        "kind": "pptx",
        "slides": 4,
        "status": "ready",
    }
    assert len(fsync_calls) == 1


def test_smoke_batch_log_is_disabled_without_environment(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("READER_SMOKE_BATCH_LOG", raising=False)
    from reader.smoke import append_smoke_batch

    assert append_smoke_batch(["C:/docs/one.md"]) is False
    assert list(tmp_path.iterdir()) == []


def test_smoke_batch_log_appends_atomic_utf8_json_lines(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "batches.jsonl"
    monkeypatch.setenv("READER_SMOKE_BATCH_LOG", str(log_path))
    from reader.smoke import append_smoke_batch

    initial = ["C:/文档/一.md", "C:/docs/two.md"]
    forwarded = ["D:/incoming/三.docx", "D:/incoming/four.xlsx"]

    assert append_smoke_batch(initial) is True
    assert append_smoke_batch(forwarded) is True

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == [initial, forwarded]
    assert len(lines) == 2


def test_enabled_smoke_batch_log_propagates_write_failure(
    monkeypatch, tmp_path: Path
) -> None:
    missing_parent_log = tmp_path / "missing" / "batches.jsonl"
    monkeypatch.setenv("READER_SMOKE_BATCH_LOG", str(missing_parent_log))
    from reader.smoke import append_smoke_batch

    with pytest.raises(OSError):
        append_smoke_batch(["C:/docs/one.md"])
