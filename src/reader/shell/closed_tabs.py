"""Recently closed file tabs, shared by all windows (Ctrl+Shift+T)."""

from __future__ import annotations

from pathlib import Path

MAX_CLOSED = 20


class ClosedTabs:
    def __init__(self) -> None:
        self._paths: list[Path] = []

    def push(self, path: Path) -> None:
        try:
            resolved = Path(path).resolve()
            if not resolved.is_file():
                return
        except OSError:
            return
        self._paths = [item for item in self._paths if item != resolved]
        self._paths.append(resolved)
        del self._paths[:-MAX_CLOSED]

    def pop(self) -> Path | None:
        """Most recently closed file that still exists, or None."""
        while self._paths:
            path = self._paths.pop()
            try:
                if path.is_file():
                    return path
            except OSError:
                continue
        return None
