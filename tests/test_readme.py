from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_lists_every_window_shortcut(qtbot):
    from reader.shell.window import MainWindow

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    window = MainWindow()
    qtbot.addWidget(window)
    for action in window.actions():
        for key in action.shortcuts():
            text = key.toString()
            if text:
                assert f"`{text}`" in readme, f"{action.text()} {text}"


def test_readme_images_exist():
    import re

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme)
    assert images
    for image in images:
        assert (ROOT / image).is_file(), image
