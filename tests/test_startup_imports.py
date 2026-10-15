from __future__ import annotations

import subprocess
import sys

HEAVY = ("docx", "pptx", "openpyxl", "numpy")


def _loaded_after(statement: str) -> list[str]:
    code = (
        f"{statement}\n"
        "import sys\n"
        f"print(','.join(m for m in {HEAVY!r} if m in sys.modules))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    return [name for name in result.stdout.strip().split(",") if name]


def test_pipeline_and_window_import_without_office_libraries():
    assert _loaded_after("import reader.preview.pipeline") == []
    assert _loaded_after("import reader.shell.window") == []


def test_office_libraries_load_when_previewing_office_files(tmp_path):
    loaded = _loaded_after(
        "from reader.formats import docx, pptx, xlsx\n"
        "import docx as _d, pptx as _p, openpyxl as _o"
    )
    assert {"docx", "pptx", "openpyxl"} <= set(loaded)