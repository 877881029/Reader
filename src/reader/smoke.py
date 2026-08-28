from __future__ import annotations

import json
import os
from pathlib import Path

SMOKE_BATCH_LOG_ENV = "READER_SMOKE_BATCH_LOG"
SMOKE_VISUAL_LOG_ENV = "READER_SMOKE_VISUAL_LOG"


def append_visual_ready(path: str, slides: int) -> bool:
    """Persist a frozen-viewer ready event when visual smoke is enabled."""
    configured_path = os.environ.get(SMOKE_VISUAL_LOG_ENV, "").strip()
    if not configured_path:
        return False

    payload = {
        "path": path,
        "kind": "pptx",
        "slides": slides,
        "status": "ready",
    }
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    with Path(configured_path).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())
    return True


def append_markdown_ready(path: str) -> bool:
    """Persist a frozen markdown-ready event when visual smoke is enabled."""
    configured_path = os.environ.get(SMOKE_VISUAL_LOG_ENV, "").strip()
    if not configured_path:
        return False

    payload = {
        "path": path,
        "kind": "markdown",
        "status": "ready",
    }
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    with Path(configured_path).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())
    return True


def append_smoke_batch(paths: list[str]) -> bool:
    """Append one received argv batch when explicit smoke telemetry is enabled."""
    configured_path = os.environ.get(SMOKE_BATCH_LOG_ENV, "").strip()
    if not configured_path:
        return False

    line = json.dumps(paths, ensure_ascii=False, separators=(",", ":")) + "\n"
    with Path(configured_path).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())
    return True
