from __future__ import annotations

import pytest

from reader.shell.browser_page import normalize_address


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("https://example.com/a?b=1", "https://example.com/a?b=1"),
        ("http://example.com", "http://example.com"),
        ("  example.com  ", "https://example.com"),
        ("docs.github.com/en", "https://docs.github.com/en"),
        ("localhost:8080", "http://localhost:8080"),
        ("localhost", "http://localhost"),
        ("file:///C:/tmp/a.html", "file:///C:/tmp/a.html"),
        ("hello world", "https://www.bing.com/search?q=hello%20world"),
        ("javascript:alert(1)", "https://www.bing.com/search?q=javascript%3Aalert(1)"),
        ("data:text/html,x", "https://www.bing.com/search?q=data%3Atext%2Fhtml%2Cx"),
        ("python", "https://www.bing.com/search?q=python"),
    ],
)
def test_normalize_address(text: str, expected: str) -> None:
    url = normalize_address(text)
    assert url is not None
    assert url.toString(url.ComponentFormattingOption.FullyEncoded) == expected


@pytest.mark.parametrize("text", ["", "   "])
def test_normalize_address_empty(text: str) -> None:
    assert normalize_address(text) is None
