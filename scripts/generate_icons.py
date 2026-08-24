from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ICON_SIZES: tuple[int, ...] = (16, 24, 32, 48, 256)
BLUE = (37, 99, 235, 255)


def _scale(points: list[tuple[float, float]], size: int) -> list[tuple[int, int]]:
    factor = size / 256
    return [(round(x * factor), round(y * factor)) for x, y in points]


def _draw_reader_r(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    width = max(2, round(34 * size / 256))

    draw.line(_scale([(72, 216), (72, 40)], size), fill=BLUE, width=width, joint="curve")
    draw.line(
        _scale([(72, 40), (142, 40), (204, 95), (142, 150), (72, 150)], size),
        fill=BLUE,
        width=width,
        joint="curve",
    )
    draw.line(_scale([(138, 150), (204, 216)], size), fill=BLUE, width=width, joint="curve")
    return image


def generate_icon_assets(root: Path) -> list[Path]:
    icon_dir = root / "assets" / "icons"
    icon_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    images: list[Image.Image] = []

    for size in ICON_SIZES:
        image = _draw_reader_r(size)
        path = icon_dir / f"reader-{size}.png"
        image.save(path)
        outputs.append(path)
        images.append(image)

    ico_path = icon_dir / "reader.ico"
    images[-1].save(
        ico_path,
        sizes=[(size, size) for size in ICON_SIZES],
        append_images=images[:-1],
    )
    outputs.append(ico_path)
    return outputs


if __name__ == "__main__":
    for generated in generate_icon_assets(Path(__file__).resolve().parents[1]):
        print(generated)
