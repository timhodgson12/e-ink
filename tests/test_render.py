"""Snapshot tests. Regenerate goldens with UPDATE_GOLDEN=1 pytest."""
import os
from datetime import datetime, time
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from eink.render import H, W, render, render_error
from eink.state import Block, State, load

ROOT = Path(__file__).parent.parent
GOLDEN = Path(__file__).parent / "golden"
EXAMPLE = ROOT / "data" / "goals.example.toml"


def at(hhmm: str, day: str = "2026-11-23") -> datetime:
    return datetime.fromisoformat(f"{day}T{hhmm}")


CASES = {
    "midmorning": lambda: load(EXAMPLE, at("10:42")),
    "between_blocks": lambda: load(EXAMPLE, at("12:20")),
    "evening": lambda: load(EXAMPLE, at("19:05")),
    "empty_day": lambda: load(EXAMPLE, at("09:00", "2026-11-26")),
    "overflow": lambda: State(
        now=at("10:05"),
        goals=[("A goal whose title is far too long to fit on one line of the panel at all", False)] * 5,
        blocks=[
            Block(time(6, 0), time(9, 0), "Starts before the window"),
            Block(time(10, 0), time(10, 10), "Tiny", focus=True),
            Block(time(10, 0), time(12, 0), "A block title that is much too long for the column"),
            Block(time(17, 0), time(21, 0), "Runs past the window", focus=True),
            Block(time(14, 0), time(13, 0), "Ends before it starts"),
        ],
        habits=[("A very long habit name indeed", [True, False, None, None, None, None, None])],
    ),
}


@pytest.mark.parametrize("name", CASES)
def test_snapshot(name):
    img = render(CASES[name]())
    assert img.mode == "1" and img.size == (W, H)
    path = GOLDEN / f"{name}.png"
    if os.environ.get("UPDATE_GOLDEN"):
        img.save(path)
    assert ImageChops.difference(img, Image.open(path).convert("1")).getbbox() is None


def test_habit_week_marks_past_misses_and_leaves_today_pending():
    s = load(EXAMPLE, at("09:00", "2026-11-25"))  # Wednesday
    assert dict(s.habits)["Move"][:4] == [False, False, None, None]
    assert dict(s.habits)["Deep work 3h"][:3] == [True, False, None]


def test_error_screen_is_panel_sized():
    img = render_error("TOMLDecodeError: " + "bad value " * 40)
    assert img.mode == "1" and img.size == (W, H)
