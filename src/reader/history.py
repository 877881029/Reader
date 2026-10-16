"""Copies of a file's previous content, taken before each save overwrites it."""

from __future__ import annotations

import hashlib
import os
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from reader.shell.recent import data_dir

MAX_VERSIONS = 20
MAX_AGE_DAYS = 30
MAX_BYTES = 10 * 1024 * 1024
_STAMP = "%Y%m%d-%H%M%S-%f"
_STAMP_LENGTH = 22
_SOURCE_FILE = "source.txt"


def default_history_dir() -> Path:
    return data_dir() / "history"


@dataclass(frozen=True)
class Version:
    path: Path
    source: Path
    saved_at: datetime
    size: int


def _atomic_write(target: Path, payload: bytes) -> None:
    fd, temp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise


class FileHistory:
    def __init__(
        self,
        root: Path,
        *,
        clock: Callable[[], float] = time.time,
        max_versions: int = MAX_VERSIONS,
        max_age_days: int = MAX_AGE_DAYS,
        max_bytes: int = MAX_BYTES,
    ) -> None:
        self.root = Path(root)
        self._clock = clock
        self._max_versions = max_versions
        self._max_age = timedelta(days=max_age_days)
        self._max_bytes = max_bytes

    def folder(self, source: Path) -> Path:
        key = str(Path(source).resolve()).lower().encode("utf-8")
        return self.root / hashlib.sha1(key).hexdigest()[:16]

    def versions(self, source: Path) -> list[Version]:
        source = Path(source).resolve()
        folder = self.folder(source)
        found = []
        try:
            entries = list(folder.iterdir())
        except OSError:
            return []
        for entry in entries:
            if entry.name == _SOURCE_FILE or entry.name.startswith("."):
                continue
            try:
                saved_at = datetime.strptime(entry.name[:_STAMP_LENGTH], _STAMP)
                size = entry.stat().st_size
            except (ValueError, OSError):
                continue
            found.append(Version(entry, source, saved_at, size))
        return sorted(found, key=lambda version: version.saved_at, reverse=True)

    def record(self, source: Path) -> Version | None:
        """Copy the file's current content into its history (before it is overwritten)."""
        source = Path(source).resolve()
        try:
            if not source.is_file() or source.stat().st_size > self._max_bytes:
                return None
            payload = source.read_bytes()
        except OSError:
            return None
        existing = self.versions(source)
        if existing:
            try:
                if existing[0].path.read_bytes() == payload:
                    return None
            except OSError:
                pass
        folder = self.folder(source)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / _SOURCE_FILE).write_text(str(source), encoding="utf-8")
        moment = datetime.fromtimestamp(self._clock())
        target = folder / f"{moment.strftime(_STAMP)}{source.suffix}"
        while target.exists():
            moment += timedelta(microseconds=1)
            target = folder / f"{moment.strftime(_STAMP)}{source.suffix}"
        _atomic_write(target, payload)
        self.prune(source)
        return Version(target, source, moment, len(payload))

    def prune(self, source: Path) -> None:
        cutoff = datetime.fromtimestamp(self._clock()) - self._max_age
        for index, version in enumerate(self.versions(source)):
            if index >= self._max_versions or version.saved_at < cutoff:
                try:
                    version.path.unlink()
                except OSError:
                    pass

    def restore(self, version: Version) -> None:
        """Write ``version`` back to its file, keeping the current content as history."""
        payload = version.path.read_bytes()
        self.record(version.source)
        _atomic_write(version.source, payload)
