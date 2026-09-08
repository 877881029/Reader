from __future__ import annotations

import json
import os
from pathlib import Path

MAX_RECENT = 12


def _is_untitled_draft(path: Path) -> bool:
    name = path.name
    return name.startswith("未命名-") and name.lower().endswith(".md")


def data_dir() -> Path:
    override = os.environ.get("READER_DATA_DIR")
    if override:
        return Path(override)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "Reader"
    return Path.home() / "Reader"


def recent_file() -> Path:
    return data_dir() / "recent.json"


def load_recent() -> list[Path]:
    path = recent_file()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    items: list[Path] = []
    for entry in raw:
        if isinstance(entry, str) and entry.strip():
            items.append(Path(entry))
    return items


def _save_recent(paths: list[Path]) -> None:
    target = recent_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = [str(path) for path in paths]
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(target)


def remember_recent(path: Path) -> list[Path]:
    if _is_untitled_draft(path):
        return load_recent()
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        resolved = path
    kept: list[Path] = []
    for item in load_recent():
        try:
            if item.resolve() == resolved:
                continue
        except OSError:
            if item == resolved:
                continue
        kept.append(item)
    kept.insert(0, resolved)
    kept = kept[:MAX_RECENT]
    _save_recent(kept)
    return kept


def visible_recent() -> list[Path]:
    loaded = load_recent()
    kept = [path for path in loaded if path.is_file()]
    if kept != loaded:
        _save_recent(kept)
    return kept
