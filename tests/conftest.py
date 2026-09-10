import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication


_app = QApplication.instance() or QApplication(sys.argv)


@pytest.fixture(autouse=True)
def isolate_reader_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("READER_DATA_DIR", str(tmp_path / "reader-data"))
    monkeypatch.setenv("READER_SKIP_WEBENGINE_WARMUP", "1")


@pytest.fixture
def tmp_file(tmp_path: Path):
    def _make(name: str, data: bytes = b"x") -> Path:
        p = tmp_path / name
        p.write_bytes(data)
        return p
    return _make
