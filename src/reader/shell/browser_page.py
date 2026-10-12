"""Lightweight in-tab web browser (``+`` → Browser)."""

from __future__ import annotations

import re
from urllib.parse import quote

from PySide6.QtCore import QUrl

SEARCH_URL = "https://www.bing.com/search?q="
_DIRECT_SCHEMES = {"http", "https", "file"}
_LOCALHOST = re.compile(r"^localhost(:\d{1,5})?(/.*)?$", re.IGNORECASE)
_HOSTLIKE = re.compile(r"^[^\s/:]+\.[^\s/:]+(:\d{1,5})?(/\S*)?$")


def normalize_address(text: str) -> QUrl | None:
    """Turn address-bar input into a safe URL; anything unusual becomes a search."""
    stripped = text.strip()
    if not stripped:
        return None
    scheme = stripped.split(":", 1)[0].lower() if ":" in stripped else ""
    if scheme in _DIRECT_SCHEMES and "://" in stripped:
        url = QUrl(stripped, QUrl.ParsingMode.StrictMode)
        if url.isValid():
            return url
    if " " not in stripped:
        if _LOCALHOST.match(stripped):
            return QUrl(f"http://{stripped}")
        if _HOSTLIKE.match(stripped):
            return QUrl(f"https://{stripped}")
    return QUrl(SEARCH_URL + quote(stripped, safe="()"), QUrl.ParsingMode.StrictMode)
