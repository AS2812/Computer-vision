"""Generate deterministic images for manually testing AgroVision locally."""

from pathlib import Path

from PIL import Image, ImageDraw


FIXTURES = Path(__file__).resolve().parent


def healthy_field() -> None:
    image = Image.new("RGB", (1280, 768), (122, 88, 52))
    draw = ImageDraw.Draw(image)

    # Twelve separated green canopies exercise vegetation segmentation and counting.
    centers = [
        (150, 160), (380, 160), (610, 160), (840, 160), (1070, 160),
        (150, 390), (380, 390), (610, 390), (840, 390), (1070, 390),
        (380, 620), (840, 620),
    ]
    for index, (x, y) in enumerate(centers):
        green = (34 + index % 3 * 5, 165 + index % 4 * 8, 45)
        draw.ellipse((x - 58, y - 58, x + 58, y + 58), fill=green)
        draw.ellipse((x - 35, y - 75, x + 35, y + 75), fill=green)
        draw.ellipse((x - 75, y - 30, x + 75, y + 30), fill=green)

    image.save(FIXTURES / "healthy_synthetic_field.png")


if __name__ == "__main__":
    FIXTURES.mkdir(parents=True, exist_ok=True)
    healthy_field()
    print(FIXTURES / "healthy_synthetic_field.png")

