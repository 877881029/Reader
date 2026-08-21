from pathlib import Path
import pytest

@pytest.fixture
def tmp_file(tmp_path: Path):
    def _make(name: str, data: bytes = b"x") -> Path:
        p = tmp_path / name
        p.write_bytes(data)
        return p
    return _make
