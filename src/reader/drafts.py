"""On-disk drafts of unsaved edits, restored after sign-out, shutdown or a crash."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from reader.shell.recent import data_dir

FORMAT_VERSION = 1
_DOC_ID = re.compile(r"[A-Za-z0-9_-]+")


def default_drafts_dir() -> Path:
    return data_dir() / "drafts"


@dataclass(frozen=True)
class Draft:
    doc_id: str
    kind: str
    path: Path | None
    suffix: str
    title: str
    text: str
    encoding: str
    bom: bool
    newline: str
    lossless: bool
    file_mtime_ns: int | None
    file_size: int | None
    saved_at: float

    def file_changed(self) -> bool:
        """True when the original file was edited or removed after the draft began."""
        if self.path is None or self.file_mtime_ns is None:
            return False
        try:
            stat = self.path.stat()
        except OSError:
            return True
        return stat.st_mtime_ns != self.file_mtime_ns or stat.st_size != self.file_size

    def to_json(self) -> dict:
        data = asdict(self)
        data["path"] = str(self.path) if self.path is not None else None
        data["version"] = FORMAT_VERSION
        return data

    @classmethod
    def from_json(cls, data: dict) -> Draft:
        if data.get("version") != FORMAT_VERSION:
            raise ValueError("unsupported draft version")
        values = {key: data[key] for key in cls.__dataclass_fields__}
        values["path"] = Path(values["path"]) if values["path"] else None
        return cls(**values)


class DraftStore:
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    def _file(self, doc_id: str) -> Path:
        if not _DOC_ID.fullmatch(doc_id or ""):
            raise ValueError(f"invalid document id: {doc_id!r}")
        return self.directory / f"{doc_id}.json"

    def save(self, draft: Draft) -> None:
        target = self._file(draft.doc_id)
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(draft.to_json(), ensure_ascii=False).encode("utf-8")
        fd, temp = tempfile.mkstemp(prefix=f".{draft.doc_id}.", suffix=".tmp", dir=self.directory)
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

    def remove(self, doc_id: str) -> None:
        try:
            self._file(doc_id).unlink()
        except FileNotFoundError:
            pass

    def load_all(self) -> list[Draft]:
        try:
            files = sorted(self.directory.glob("*.json"))
        except OSError:
            return []
        drafts = []
        for file in files:
            try:
                drafts.append(Draft.from_json(json.loads(file.read_text(encoding="utf-8"))))
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return sorted(drafts, key=lambda draft: (draft.saved_at, draft.doc_id))
