"""Snapshot tests. Regenerate goldens with UPDATE_GOLDEN=1 pytest."""
import json
import os
from datetime import datetime, time, timedelta
from pathlib import Path

import pytest
from PIL import Image, ImageChops

import eink.weather as weather
from eink.render import H, W, render, render_error
from eink.state import Block, State, Weather, load

ROOT = Path(__file__).parent.parent
GOLDEN = Path(__file__).parent / "golden"
EXAMPLE = ROOT / "data" / "goals.example.toml"


def at(hhmm: str, day: str = "2026-11-23") -> datetime:
    return datetime.fromisoformat(f"{day}T{hhmm}")


def wx(**over) -> Weather:
    d = dict(icon="drizzle", hi=9, lo=6, rain=60, note="light rain likely 11:00–14:00")
    d.update(over)
    return Weather(**d)


CASES = {
    "midmorning": lambda: (load(EXAMPLE, at("10:42")), None),
    "midmorning_wx": lambda: (load(EXAMPLE, at("10:42")), wx()),
    "midmorning_dry": lambda: (load(EXAMPLE, at("10:42")), wx(icon="part", hi=11, lo=8, rain=10, note="")),
    "between_blocks": lambda: (load(EXAMPLE, at("12:20")), None),
    "evening": lambda: (load(EXAMPLE, at("19:05")), None),
    "morning": lambda: (load(EXAMPLE, at("07:20")), None),
    "empty_day": lambda: (load(EXAMPLE, at("09:00", "2026-11-26")), None),
    "alldone": lambda: (
        State(
            now=at("16:10"),
            goals=[(t, True) for t, _ in load(EXAMPLE, at("16:10")).goals],
            blocks=load(EXAMPLE, at("16:10")).blocks,
            habits=load(EXAMPLE, at("16:10")).habits,
        ),
        None,
    ),
    "overflow": lambda: (
        State(
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
        wx(icon="rain", hi=8, lo=7, rain=85, note="heavy rain from 13:00, 4 mm"),
    ),
}


@pytest.mark.parametrize("name", CASES)
def test_snapshot(name):
    s, wxv = CASES[name]()
    img = render(s, wxv)
    assert img.mode == "1" and img.size == (W, H)
    path = GOLDEN / f"{name}.png"
    if os.environ.get("UPDATE_GOLDEN"):
        img.save(path)
    assert ImageChops.difference(img, Image.open(path).convert("1")).getbbox() is None


def test_screen_selection():
    s = lambda hhmm: load(EXAMPLE, at(hhmm))
    assert render(s("07:20")).getbbox() == render(s("07:20"), wx()).getbbox()  # morning: no dock
    # between: the day view without a current block still differs from the gap screen
    assert render(s("12:20")) != render(s("10:42"))
    # dock present only when weather is known
    day, day_wx = render(s("10:42")), render(s("10:42"), wx())
    diff = ImageChops.difference(day, day_wx).getbbox()
    assert diff is not None and diff[0] >= 520  # left content identical; delta in the timeline/dock column


def test_habit_week_marks_past_misses_and_leaves_today_pending():
    s = load(EXAMPLE, at("09:00", "2026-11-25"))  # Wednesday
    assert dict(s.habits)["Move"][:4] == [False, False, None, None]
    assert dict(s.habits)["Deep work 3h"][:3] == [True, False, None]


def test_weather_dock_region_static_between_minutes():
    """Minute ticks move clock/progress/now-marker; the dock band must be identical."""
    s1, s2 = load(EXAMPLE, at("10:42")), load(EXAMPLE, at("10:43"))
    a, b = render(s1, wx()), render(s2, wx())
    dock = (520, 416, 800, 480)
    ac, bc = a.crop(dock), b.crop(dock)
    assert ImageChops.difference(ac, bc).getbbox() is None


def test_error_screen_is_panel_sized():
    img = render_error("TOMLDecodeError: " + "bad value " * 40)
    assert img.mode == "1" and img.size == (W, H)


# ── eink.weather: cache behaviour, icon mapping, degrade to None ─────────────

def test_weather_current_reads_fresh_cache(tmp_path, monkeypatch):
    cache = tmp_path / "weather.json"
    cache.write_text(json.dumps({"fetched": datetime.now().isoformat(), "icon": "sun", "hi": 12, "lo": 4, "rain": 5}))
    monkeypatch.setattr(weather, "CACHE", cache)
    monkeypatch.setattr(weather, "fetch", lambda: pytest.fail("fresh cache must not refetch"))
    w = weather.current()
    assert (w.icon, w.hi, w.lo, w.rain) == ("sun", 12, 4, 5)


def test_weather_stale_cache_refetches_and_caches(tmp_path, monkeypatch):
    cache = tmp_path / "weather.json"
    stale = dict(fetched=(datetime.now() - timedelta(minutes=90)).isoformat(),
                 icon="cloud", hi=7, lo=3, rain=20)
    cache.write_text(json.dumps(stale))

    def fake_fetch():
        w = Weather("rain", 8, 2, 90, "soaked")
        cache.write_text(json.dumps({"fetched": datetime.now().isoformat(), **w.__dict__}))
        return w

    monkeypatch.setattr(weather, "CACHE", cache)
    monkeypatch.setattr(weather, "fetch", fake_fetch)
    assert weather.current().rain == 90
    assert json.loads(cache.read_text())["icon"] == "rain"


def test_weather_degrades_to_none_without_cache_or_network(tmp_path, monkeypatch):
    monkeypatch.setattr(weather, "CACHE", tmp_path / "missing.json")
    monkeypatch.setattr(weather, "fetch", lambda: (_ for _ in ()).throw(OSError("no route")))
    assert weather.current() is None


def test_weather_stale_cache_used_when_fetch_fails(tmp_path, monkeypatch):
    cache = tmp_path / "weather.json"
    cache.write_text(json.dumps({"fetched": (datetime.now() - timedelta(hours=5)).isoformat(),
                                 "icon": "part", "hi": 9, "lo": 1, "rain": 0, "note": ""}))
    monkeypatch.setattr(weather, "CACHE", cache)
    monkeypatch.setattr(weather, "fetch", lambda: (_ for _ in ()).throw(OSError("offline")))
    w = weather.current()
    assert w is not None and w.icon == "part"  # stale beats nothing


def test_weather_icon_mapping():
    code_icon = {0: "sun", 1: "part", 2: "part", 3: "cloud", 61: "drizzle", 63: "drizzle", 65: "rain", 95: "rain"}
    for code, want in code_icon.items():
        assert weather._icon(code) == want
