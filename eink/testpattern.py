"""Calibration image for the camera loop: python -m eink.testpattern [--out x.png]"""
import argparse

from PIL import Image, ImageDraw

from .render import BLACK, H, W, WHITE, font, to_1bit


def pattern() -> Image.Image:
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=BLACK)            # outermost pixels: window alignment
    for x, y in [(0, 0), (W - 41, 0), (0, H - 41), (W - 41, H - 41)]:
        d.rectangle([x, y, x + 40, y + 40], fill=BLACK)          # corner fiducials for deskew
    for x in range(100, W, 100):
        d.line([x, 0, x, H], fill=BLACK)
    for y in range(80, H, 80):
        d.line([0, y, W, y], fill=BLACK)
    y = 90
    for size in (12, 14, 16, 20, 28, 40):                        # smallest legible text
        for wgt, x in (("R", 110), ("B", 460)):
            d.text((x, y), f"{size}px Goals 0189"[: 24 if size < 40 else 12], font=font(wgt, size), fill=BLACK)
        y += size + 14
    for i, n in enumerate((1, 2, 3, 4)):                         # n-px stripes: resolution / ghosting
        x0 = 110 + i * 110
        for k in range(0, 90, 2 * n):
            d.rectangle([x0 + k, 340, x0 + k + n - 1, 430], fill=BLACK)
    d.rectangle([560, 340, 690, 430], fill=BLACK)                # solid patch: contrast reference
    return to_1bit(img)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args()
    from .display import EpdDisplay, PngDisplay

    (PngDisplay(a.out) if a.out else EpdDisplay()).show(pattern(), full=True)
