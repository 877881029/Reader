from __future__ import annotations

import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
    if getattr(sys, "frozen", False):
        root = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        root = Path(__file__).resolve().parents[2]
    return root.joinpath(*parts)
