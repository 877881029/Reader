import importlib.util
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "assets" / "icons"
ICON_SIZES = (16, 24, 32, 48, 256)


def _xy(size: int, x_norm: float, y_norm: float) -> tuple[int, int]:
    x = min(size - 1, max(0, round(size * x_norm)))
    y = min(size - 1, max(0, round(size * y_norm)))
    return x, y


def _assert_key_pixels(image: Image.Image, size: int) -> None:
    outside = image.getpixel(_xy(size, 0.03, 0.03))
    counter = image.getpixel(_xy(size, 0.60, 0.33))
    stroke = image.getpixel(_xy(size, 0.305, 0.50))
    assert outside[3] == 0
    assert counter[3] == 0
    assert stroke[3] > 0
    assert stroke[2] >= stroke[1] + 80
    assert stroke[1] >= stroke[0] + 40
    assert stroke[2] > stroke[1] > stroke[0]


def _load_generator_module():
    script_path = ROOT / "scripts" / "generate_icons.py"
    spec = importlib.util.spec_from_file_location("generate_icons_module", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_png_frames_have_exact_mode_size_and_key_pixels():
    for size in ICON_SIZES:
        with Image.open(ICON_DIR / f"reader-{size}.png") as image:
            assert image.mode == "RGBA"
            assert image.size == (size, size)
            _assert_key_pixels(image, size)


def test_ico_frames_are_decodable_and_match_key_pixels():
    with Image.open(ICON_DIR / "reader.ico") as icon:
        assert icon.format == "ICO"
        target_sizes = {(size, size) for size in ICON_SIZES}
        available = set(icon.ico.sizes())
        assert target_sizes <= available
        for size in ICON_SIZES:
            frame = icon.ico.getimage((size, size))
            frame.load()
            assert frame.size == (size, size)
            assert frame.mode == "RGBA"
            _assert_key_pixels(frame, size)


def test_png_and_ico_frames_retain_full_transparency_and_full_opacity():
    images = []
    for size in ICON_SIZES:
        with Image.open(ICON_DIR / f"reader-{size}.png") as image:
            images.append(image.convert("RGBA"))
    with Image.open(ICON_DIR / "reader.ico") as icon:
        images.extend(
            icon.ico.getimage((size, size)).convert("RGBA")
            for size in ICON_SIZES
        )

    for image in images:
        assert image.getchannel("A").getextrema() == (0, 255)


def test_svg_and_generator_share_same_contour_paths():
    module = _load_generator_module()
    assert hasattr(module, "R_PATHS")
    path_data = tuple(module.R_PATHS)
    assert len(path_data) >= 3

    svg_text = (ICON_DIR / "reader-r.svg").read_text(encoding="utf-8")
    for contour in path_data:
        assert f'd="{contour}"' in svg_text
