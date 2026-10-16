"""Bump Reader's version before each release.

    python scripts\\bump_version.py            # 0.1.0 -> 0.1.1
    python scripts\\bump_version.py --minor    # 0.1.3 -> 0.2.0
    python scripts\\bump_version.py --major    # 0.2.0 -> 1.0.0
    python scripts\\bump_version.py --set 1.0.0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import version_tools  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bump Reader's VERSION")
    parser.add_argument("--root", type=Path, default=ROOT)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--minor", action="store_true")
    group.add_argument("--major", action="store_true")
    group.add_argument("--set", dest="exact")
    args = parser.parse_args(argv)

    try:
        current = version_tools.read_version(args.root)
        if args.exact is not None:
            version_tools.parse(args.exact)
            new = args.exact.strip()
        else:
            part = "major" if args.major else "minor" if args.minor else "patch"
            new = version_tools.bumped(current, part)
        version_tools.apply_version(args.root, new)
    except (OSError, ValueError) as exc:
        print(f"版本号未修改：{exc}", file=sys.stderr)
        return 1
    print(f"{current} -> {new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
