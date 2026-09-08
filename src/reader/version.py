from __future__ import annotations

from reader.resources import resource_path


def product_version() -> str:
    path = resource_path("VERSION")
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.1.0"
    line = text.splitlines()[0].strip() if text else ""
    return line or "0.1.0"
