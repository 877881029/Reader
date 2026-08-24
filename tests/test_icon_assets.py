from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "assets" / "icons"


def test_icon_files_exist():
    expected = [
        "reader-r.svg",
        "reader-16.png",
        "reader-24.png",
        "reader-32.png",
        "reader-48.png",
        "reader-256.png",
        "reader.ico",
    ]
    assert [name for name in expected if not (ICON_DIR / name).exists()] == []


def test_png_alpha_is_transparent_outside_and_inside_counter():
    image = Image.open(ICON_DIR / "reader-256.png").convert("RGBA")
    assert image.getpixel((8, 8))[3] == 0
    assert image.getpixel((154, 84))[3] == 0
    assert image.getpixel((78, 128))[3] == 255


def test_ico_contains_multiple_transparent_sizes():
    icon = Image.open(ICON_DIR / "reader.ico")
    assert {size for size in icon.ico.sizes()} >= {(16, 16), (24, 24), (32, 32), (48, 48), (256, 256)}
