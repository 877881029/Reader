from __future__ import annotations

import json
import os
from pathlib import Path

SMOKE_BATCH_LOG_ENV = "READER_SMOKE_BATCH_LOG"


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
