from __future__ import annotations

import json
from pathlib import Path

from reader.terminal.selftest import MARKER, run_pty_selftest


def test_pty_selftest_reports_success(tmp_path: Path):
    output = tmp_path / "pty.json"

    assert run_pty_selftest(output) == 0

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["ok"] is True
    assert result["shell"].lower().endswith("cmd.exe")
    assert MARKER in result["tail"]


def test_main_dispatches_selftest_without_gui(tmp_path: Path, monkeypatch):
    import reader.__main__ as entry

    output = tmp_path / "pty.json"
    calls: list[Path] = []
    monkeypatch.setattr(entry, "run_pty_selftest", lambda path: calls.append(Path(path)) or 0)
    monkeypatch.setattr(entry, "QApplication", None)

    assert entry.main(["Reader.exe", "--pty-selftest", str(output)]) == 0
    assert calls == [output]