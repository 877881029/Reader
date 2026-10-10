import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication


_app = QApplication.instance() or QApplication(sys.argv)


@pytest.fixture(autouse=True)
def isolate_reader_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("READER_DATA_DIR", str(tmp_path / "reader-data"))
    monkeypatch.setenv("READER_SKIP_WEBENGINE_WARMUP", "1")


_REAL_ASK_UNSAVED = None


@pytest.fixture(autouse=True)
def never_block_on_unsaved_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    global _REAL_ASK_UNSAVED
    from reader.shell.window import MainWindow

    if _REAL_ASK_UNSAVED is None:
        _REAL_ASK_UNSAVED = MainWindow._ask_unsaved_changes
    monkeypatch.setattr(MainWindow, "_ask_unsaved_changes", lambda _self, _name: "discard")


@pytest.fixture
def real_unsaved_prompt():
    return _REAL_ASK_UNSAVED


@pytest.fixture
def tmp_file(tmp_path: Path):
    def _make(name: str, data: bytes = b"x") -> Path:
        p = tmp_path / name
        p.write_bytes(data)
        return p
    return _make
