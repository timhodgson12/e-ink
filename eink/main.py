"""Render loop. On the Pi: python -m eink.main    On a PC: python -m eink.main --once --out out.png"""
import argparse
import time
from datetime import datetime

from .display import EpdDisplay, PngDisplay
from .render import render, render_error
from .state import load


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/goals.toml")
    ap.add_argument("--out", help="write a PNG instead of driving the panel")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--at", help="pretend it is this time, e.g. 2026-11-23T10:42")
    args = ap.parse_args()

    disp = PngDisplay(args.out) if args.out else EpdDisplay()
    last, last_full_hour = None, None
    while True:
        now = datetime.fromisoformat(args.at) if args.at else datetime.now()
        try:
            img = render(load(args.data, now))
        except Exception as e:  # bad TOML, missing file: show it on the panel
            img = render_error(f"{type(e).__name__}: {e}")
        if img.tobytes() != last:
            # full refresh on start and once an hour clears partial-refresh ghosting
            full = last is None or now.hour != last_full_hour
            disp.show(img, full=full)
            last = img.tobytes()
            if full:
                last_full_hour = now.hour
        if args.once:
            return
        time.sleep(60 - time.time() % 60 + 0.5)  # wake just after each minute


if __name__ == "__main__":
    main()
