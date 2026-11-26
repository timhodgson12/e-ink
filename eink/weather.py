"""Day outlook for the weather dock, via Open-Meteo (no API key).

The fetch runs Pi-side at most hourly; the last good result is cached to
data/weather.json and the renderer only ever reads that cache. Any failure
(missing cache, stale cache, no network) degrades to `None` — the day screen
just renders without the dock.

Location defaults to the workshop; override with EINK_LAT / EINK_LON.
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from .state import Weather

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "weather.json"
CACHE_TTL = timedelta(hours=1)
FETCH_TIMEOUT = 10

LAT = float(os.environ.get("EINK_LAT", "52.09"))
LON = float(os.environ.get("EINK_LON", "5.12"))  # TODO Tim: the display's location

URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode"
    "&hourly=precipitation_probability,weathercode"
    "&timezone=auto&forecast_days=1"
)


def _icon(code: int) -> str:
    if code == 0:
        return "sun"
    if code in (1, 2):
        return "part"
    if code == 3:
        return "cloud"
    if code in (51, 53, 55, 56, 57, 61, 63, 80):  # drizzle family, light showers
        return "drizzle"
    return "rain"  # heavy rain, snow, showers, storms — one umbrella icon


def _hour_of(iso: str) -> int:
    return int(iso[11:13])


def _from_api(payload: dict) -> Weather:
    daily = payload["daily"]
    hourly = payload["hourly"]
    now_h = datetime.now().hour

    # remaining today: worst rain chance and first wet spell still ahead
    probs = [p for h, p in zip(hourly["time"], hourly["precipitation_probability"]) if _hour_of(h) >= now_h]
    rain = max(probs) if probs else (daily["precipitation_probability_max"] or [0])[0]
    note = ""
    for h, p in zip(hourly["time"], hourly["precipitation_probability"]):
        hour = _hour_of(h)
        if hour >= now_h and p is not None and p >= 60:
            note = f"rain likely from {hour:02d}:00"
            break
    return Weather(
        icon=_icon(int(daily["weathercode"][0])),
        hi=round(daily["temperature_2m_max"][0]),
        lo=round(daily["temperature_2m_min"][0]),
        rain=int(rain or 0),
        note=note,
    )


def fetch() -> Weather:
    """Live fetch. Raises on network/API trouble; callers decide the fallback."""
    with urllib.request.urlopen(URL, timeout=FETCH_TIMEOUT) as r:
        payload = json.load(r)
    wx = _from_api(payload)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({"fetched": datetime.now().isoformat(timespec="seconds"),
                                 "icon": wx.icon, "hi": wx.hi, "lo": wx.lo,
                                 "rain": wx.rain, "note": wx.note}))
    return wx


def current(max_age: timedelta = CACHE_TTL) -> Weather | None:
    """Cache-first accessor for the render loop: refresh hourly, degrade to None."""
    cached = None
    if CACHE.exists():
        try:
            cached = json.loads(CACHE.read_text())
        except (json.JSONDecodeError, OSError):
            cached = None
    fresh = cached is not None and datetime.now() - datetime.fromisoformat(cached["fetched"]) < max_age
    if not fresh:
        try:
            return fetch()
        except Exception:  # no network, API down: stale cache beats nothing
            pass
    if cached is not None:
        return Weather(cached["icon"], cached["hi"], cached["lo"], cached["rain"], cached.get("note", ""))
    return None
