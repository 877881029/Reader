from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reader.sniff import SniffError, sniff


@dataclass(frozen=True)
class OpenDecision:
    to_open: tuple[Path, ...]
    to_focus: Path | None
    rejected: tuple[tuple[Path, str], ...]


def decide_open(existing: list[Path], incoming: list[Path]) -> OpenDecision:
    known = [Path(p).resolve() for p in existing]
    to_open: list[Path] = []
    rejected: list[tuple[Path, str]] = []
    to_focus: Path | None = None

    for raw in incoming:
        path = Path(raw)
        try:
            sniff(path)
        except SniffError as exc:
            rejected.append((exc.path, exc.reason))
            continue

        resolved = path.resolve()
        if resolved in known:
            to_focus = resolved
            continue

        to_open.append(resolved)
        known.append(resolved)

    return OpenDecision(tuple(to_open), to_focus, tuple(rejected))
