"""Viewer startup timeout must fall back to text, not crash the process.

Run in a child process: the bug was a native access violation in Qt WebEngine
(clearing the page's user scripts right before setHtml while it was loading).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_SCRIPT = r"""
import sys
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
kind, source, delay = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3])
if kind == "pptx":
    from reader.formats import pptx as fmt
    from reader.preview.pptx_view import PptxVisualView as View
else:
    from reader.formats import md as fmt
    from reader.preview.md_view import MarkdownVisualView as View
view = View(fmt.to_visual(source), source)
failures = []
view.render_failed.connect(failures.append)
view.resize(800, 600)
view.show()
view.start()
QTimer.singleShot(delay, view._startup_timeout)

def done():
    print("ALIVE", view.is_fallback, bool(failures), flush=True)
    view.shutdown()
    app.quit()

QTimer.singleShot(delay + 2500, done)
app.exec()
"""


@pytest.mark.parametrize(
    ("kind", "source"),
    [
        ("pptx", ROOT / "tests" / "fixtures" / "pptx" / "visual-elements.pptx"),
        ("md", ROOT / "tests" / "fixtures" / "md" / "visual-document.md"),
    ],
)
@pytest.mark.parametrize("delay", [50, 300])
def test_startup_timeout_falls_back_without_crashing(tmp_path, kind, source, delay):
    env = dict(os.environ)
    env["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
    env["READER_DATA_DIR"] = str(tmp_path)
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-c", _SCRIPT, kind, str(source), str(delay)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=120,
    )

    assert "ALIVE True True" in result.stdout, (result.returncode, result.stderr[-2000:])
    assert result.returncode == 0
