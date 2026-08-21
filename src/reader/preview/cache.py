from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path

from reader.preview.result import PreviewResult

_ACCESS_FILE = "last_access_ns.txt"
_META_FILE = "meta.json"
_HTML_FILE = "preview.html"
_PDF_FILE = "preview.pdf"


def cache_dir() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        base = Path(local_appdata)
    else:
        base = Path.home() / "AppData" / "Local"
    return base / "Reader" / "preview-cache"


class PreviewCache:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else cache_dir()
        self._ensure_root()

    def _ensure_root(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def _key(self, path: Path, strategy: str) -> str:
        resolved = path.resolve()
        st = resolved.stat()
        payload = f"{resolved}|{st.st_mtime_ns}|{st.st_size}|{strategy}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _slot(self, key: str) -> Path:
        return self.root / key

    def _touch_access(self, slot: Path) -> None:
        access_path = slot / _ACCESS_FILE
        access_path.write_text(str(time.time_ns()), encoding="utf-8")

    def get(self, path: Path, strategy: str) -> PreviewResult | None:
        try:
            key = self._key(path, strategy)
        except OSError:
            return None
        slot = self._slot(key)
        meta = slot / _META_FILE
        if not meta.exists():
            return None

        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None

        kind = data.get("kind")
        status_label = data.get("status_label")
        if not isinstance(kind, str) or not isinstance(status_label, str):
            return None

        try:
            if kind == "html":
                html = (slot / _HTML_FILE).read_text(encoding="utf-8")
                result = PreviewResult(
                    html=html,
                    status_label=status_label,
                    kind="html",
                    error=data.get("error"),
                )
            elif kind == "pdf":
                pdf = slot / _PDF_FILE
                if not pdf.exists():
                    return None
                result = PreviewResult(
                    html=data.get("html", ""),
                    status_label=status_label,
                    kind="pdf",
                    pdf_path=pdf,
                    error=data.get("error"),
                )
            else:
                return None
        except OSError:
            return None

        try:
            self._touch_access(slot)
        except OSError:
            pass
        return result

    def put(self, path: Path, strategy: str, result: PreviewResult) -> None:
        self._ensure_root()
        key = self._key(path, strategy)
        slot = self._slot(key)
        shutil.rmtree(slot, ignore_errors=True)
        slot.mkdir(parents=True, exist_ok=True)

        meta = {
            "status_label": result.status_label,
            "kind": result.kind,
            "html": result.html if result.kind == "pdf" else "",
            "error": result.error,
        }
        (slot / _META_FILE).write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

        if result.kind == "html":
            (slot / _HTML_FILE).write_text(result.html, encoding="utf-8")
        elif result.kind == "pdf":
            if result.pdf_path is None:
                shutil.rmtree(slot, ignore_errors=True)
                raise ValueError("pdf result requires pdf_path")
            (slot / _PDF_FILE).write_bytes(result.pdf_path.read_bytes())

        self._touch_access(slot)
        self.enforce_limit()

    def _slot_size(self, slot: Path) -> int:
        size = 0
        for f in slot.rglob("*"):
            if f.is_file():
                try:
                    size += f.stat().st_size
                except OSError:
                    continue
        return size

    def _slot_last_access(self, slot: Path) -> int:
        access_path = slot / _ACCESS_FILE
        if access_path.exists():
            try:
                return int(access_path.read_text(encoding="utf-8").strip())
            except (OSError, ValueError, UnicodeDecodeError):
                pass
        try:
            return slot.stat().st_mtime_ns
        except OSError:
            return 0

    def enforce_limit(self, max_bytes: int = 200 * 1024 * 1024) -> None:
        if not self.root.exists():
            return

        entries: list[tuple[int, Path, int]] = []
        total = 0
        try:
            roots = list(self.root.iterdir())
        except OSError:
            return

        for slot in roots:
            if not slot.is_dir():
                continue
            size = self._slot_size(slot)
            last_access = self._slot_last_access(slot)
            entries.append((last_access, slot, size))
            total += size

        entries.sort(key=lambda item: item[0])
        for _last_access, slot, size in entries:
            if total <= max_bytes:
                break
            shutil.rmtree(slot, ignore_errors=True)
            total -= size
