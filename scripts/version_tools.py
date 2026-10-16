"""Version helpers shared by ``bump_version.py`` and ``reader.spec``.

``VERSION`` (one ``MAJOR.MINOR.PATCH`` line) is the only place the version is written.
"""

from __future__ import annotations

import re
from pathlib import Path

_SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)")
_README_LINE = re.compile(r"当前版本 \*\*\d+\.\d+\.\d+\*\*")


def parse(version: str) -> tuple[int, int, int]:
    match = _SEMVER.fullmatch(version.strip())
    if match is None:
        raise ValueError(f"版本号必须是 主.次.修订，例如 1.0.3：{version!r}")
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def read_version(root: Path) -> str:
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    parse(version)
    return version


def bumped(version: str, part: str = "patch") -> str:
    major, minor, patch = parse(version)
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"未知的版本部分：{part}")


def _rewrite(path: Path, transform) -> None:
    if not path.is_file():
        return
    raw = path.read_bytes().decode("utf-8")
    updated = transform(raw)
    if updated != raw:
        path.write_bytes(updated.encode("utf-8"))


def apply_version(root: Path, version: str) -> None:
    """Write ``version`` to VERSION and the README "当前版本" line."""
    parse(version)
    (root / "VERSION").write_bytes((version + "\n").encode("utf-8"))
    _rewrite(
        root / "README.md",
        lambda text: _README_LINE.sub(f"当前版本 **{version}**", text, count=1),
    )


def win32_version_info(version: str) -> str:
    """PyInstaller ``version=`` file content for Reader.exe."""
    major, minor, patch = parse(version)
    numbers = f"({major}, {minor}, {patch}, 0)"
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numbers},
    prodvers={numbers},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'Reader'),
          StringStruct('FileDescription', 'Reader'),
          StringStruct('FileVersion', '{version}'),
          StringStruct('InternalName', 'Reader'),
          StringStruct('OriginalFilename', 'Reader.exe'),
          StringStruct('ProductName', 'Reader'),
          StringStruct('ProductVersion', '{version}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def write_win32_version_info(root: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(win32_version_info(read_version(root)), encoding="utf-8")
    return target
