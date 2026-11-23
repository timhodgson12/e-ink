"""Display backends: the real panel on the Pi, or a PNG file for development."""
from pathlib import Path

from PIL import Image


class PngDisplay:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def show(self, img: Image.Image, full: bool) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        img.save(self.path)


class EpdDisplay:
    """Waveshare 7.5" V2 (800x480 B/W). UNTESTED until hardware arrives.

    Needs the `waveshare-epd` package and SPI enabled. Method names follow the
    current Waveshare epd7in5_V2 driver; partial refresh is used only if the
    installed driver exposes it.
    """

    def __init__(self):
        from waveshare_epd import epd7in5_V2  # only importable on the Pi

        self.epd = epd7in5_V2.EPD()
        self.partial = hasattr(self.epd, "init_part") and hasattr(self.epd, "display_Partial")

    def show(self, img: Image.Image, full: bool) -> None:
        epd = self.epd
        if full or not self.partial:
            epd.init()
            epd.display(epd.getbuffer(img))
        else:
            epd.init_part()
            epd.display_Partial(epd.getbuffer(img), 0, 0, epd.width, epd.height)
        epd.sleep()  # never leave the panel powered between updates
