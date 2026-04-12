"""Generate apple-touch-icon.png (180x180) matching the SVG favicon."""

# ruff: noqa: INP001

from PIL import Image, ImageDraw

FINAL = 180
SUPERSAMPLE = 4  # render at 4x then downscale for anti-aliasing
SIZE = FINAL * SUPERSAMPLE
SCALE = SIZE / 280  # SVG viewBox is 0 0 280 280


def s(v: float) -> float:
    """Scale SVG coordinate to pixel coordinate."""
    return v * SCALE


def main() -> None:
    """Render the favicon as a 180x180 PNG with 4x super sampling."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Blue rounded background
    draw.rounded_rectangle(
        [0, 0, SIZE - 1, SIZE - 1], radius=int(s(40)), fill="#2563eb"
    )

    # Column headers (white, low opacity)
    for x in (24, 106, 188):
        draw.rounded_rectangle(
            [s(x), s(36), s(x + 68), s(36 + 8)],
            radius=int(s(4)),
            fill=(255, 255, 255, 89),
        )

    # Column backgrounds
    for x in (24, 106, 188):
        draw.rounded_rectangle(
            [s(x), s(54), s(x + 68), s(54 + 188)],
            radius=int(s(8)),
            fill="#1d4ed8",
        )

    # Cards — column 1
    for y, h, opacity in [
        (62, 30, 0.95),
        (100, 30, 0.95),
        (138, 30, 0.75),
        (176, 20, 0.4),
    ]:
        draw.rounded_rectangle(
            [s(32), s(y), s(32 + 52), s(y + h)],
            radius=int(s(5)),
            fill=(255, 255, 255, int(opacity * 255)),
        )

    # Cards — column 2
    for y, h, opacity in [(62, 30, 0.95), (100, 30, 0.75), (138, 20, 0.4)]:
        draw.rounded_rectangle(
            [s(114), s(y), s(114 + 52), s(y + h)],
            radius=int(s(5)),
            fill=(255, 255, 255, int(opacity * 255)),
        )

    # Cards — column 3
    for y, h, opacity in [(62, 30, 0.75), (100, 20, 0.4)]:
        draw.rounded_rectangle(
            [s(196), s(y), s(196 + 52), s(y + h)],
            radius=int(s(5)),
            fill=(255, 255, 255, int(opacity * 255)),
        )

    # Green check mark circle
    cx, cy, r = s(212), s(212), s(56)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#16a34a")

    # Check mark polyline (thick)
    points = [(s(188), s(212)), (s(206), s(232)), (s(240), s(192))]
    draw.line(points, fill="#22c55e", width=max(int(s(14)), 2), joint="curve")

    # Downscale with high-quality Lanczos resampling
    img = img.resize((FINAL, FINAL), Image.LANCZOS)
    img.save("src/icons/apple-touch-icon.png", "PNG")
    print("Created src/icons/apple-touch-icon.png")


if __name__ == "__main__":
    main()

# cspell:ignore: Lanczos SUPERSAMPLE
