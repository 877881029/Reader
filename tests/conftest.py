import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication


_app = QApplication.instance() or QApplication(sys.argv)


@pytest.fixture
def tmp_file(tmp_path: Path):
    def _make(name: str, data: bytes = b"x") -> Path:
        p = tmp_path / name
        p.write_bytes(data)
        return p
    return _make
