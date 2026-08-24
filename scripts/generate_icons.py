from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw

ICON_SIZES: tuple[int, ...] = (16, 24, 32, 48, 256)
BLUE = (37, 99, 235, 255)
STROKE_WIDTH = 34.0
SUPERSAMPLE = 6
CURVE_STEPS = 48
R_PATHS: tuple[str, ...] = (
    "M72 216 L72 40",
    "M72 40 L140 40 C176 40 202 60 202 95 C202 130 176 150 140 150 L72 150",
    "M136 150 C150 152 166 164 178 178 C188 190 197 202 204 216",
)


def _tokenize_path(path_data: str) -> list[str]:
    return re.findall(r"[MLC]|-?\d+(?:\.\d+)?", path_data)


def _cubic_point(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    omt = 1.0 - t
    x = (omt**3) * p0[0] + 3 * (omt**2) * t * p1[0] + 3 * omt * (t**2) * p2[0] + (t**3) * p3[0]
    y = (omt**3) * p0[1] + 3 * (omt**2) * t * p1[1] + 3 * omt * (t**2) * p2[1] + (t**3) * p3[1]
    return (x, y)


def _sample_svg_path(path_data: str, steps: int = CURVE_STEPS) -> list[tuple[float, float]]:
    tokens = _tokenize_path(path_data)
    i = 0
    points: list[tuple[float, float]] = []
    current = (0.0, 0.0)

    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        if cmd == "M":
            x = float(tokens[i])
            y = float(tokens[i + 1])
            i += 2
            current = (x, y)
            points.append(current)
            continue
        if cmd == "L":
            x = float(tokens[i])
            y = float(tokens[i + 1])
            i += 2
            current = (x, y)
            points.append(current)
            continue
        if cmd == "C":
            p1 = (float(tokens[i]), float(tokens[i + 1]))
            p2 = (float(tokens[i + 2]), float(tokens[i + 3]))
            p3 = (float(tokens[i + 4]), float(tokens[i + 5]))
            i += 6
            p0 = current
            for step in range(1, steps + 1):
                t = step / steps
                points.append(_cubic_point(p0, p1, p2, p3, t))
            current = p3
            continue
        raise ValueError(f"Unsupported path command: {cmd}")
    return points


def _scale(points: list[tuple[float, float]], size: int) -> list[tuple[int, int]]:
    factor = (size * SUPERSAMPLE) / 256
    return [(round(x * factor), round(y * factor)) for x, y in points]


def _draw_reader_r(size: int) -> Image.Image:
    hi_size = size * SUPERSAMPLE
    image = Image.new("RGBA", (hi_size, hi_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    width = max(2 * SUPERSAMPLE, round(STROKE_WIDTH * size * SUPERSAMPLE / 256))

    for path_data in R_PATHS:
        draw.line(_scale(_sample_svg_path(path_data), size), fill=BLUE, width=width, joint="curve")

    return image.resize((size, size), resample=Image.Resampling.LANCZOS)


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
        format="ICO",
        sizes=[(size, size) for size in ICON_SIZES],
    )
    outputs.append(ico_path)
    return outputs


if __name__ == "__main__":
    for generated in generate_icon_assets(Path(__file__).resolve().parents[1]):
        print(generated)
