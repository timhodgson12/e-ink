"""Display state, loaded from a TOML file (see data/goals.example.toml)."""
import tomllib
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path


@dataclass
class Block:
    start: time
    end: time
    title: str
    focus: bool = False  # focus blocks draw solid, the rest outlined


@dataclass
class State:
    now: datetime
    goals: list[tuple[str, bool]]
    blocks: list[Block]
    habits: list[tuple[str, list[bool | None]]]  # Mon..Sun; None = not yet
    day_start: time = time(8, 0)
    day_end: time = time(18, 0)


def _hm(s: str) -> time:
    return time.fromisoformat(s)


def load(path: str | Path, now: datetime | None = None) -> State:
    now = now or datetime.now()
    raw = tomllib.loads(Path(path).read_text())
    day = raw.get("days", {}).get(now.date().isoformat(), {})
    monday = now.date() - timedelta(days=now.weekday())
    habits = []
    for h in raw.get("habits", []):
        done = {date.fromisoformat(str(d)) for d in h.get("done", [])}
        week = []
        for i in range(7):
            d = monday + timedelta(days=i)
            # today stays "pending" until ticked; only past days count as missed
            week.append(True if d in done else (False if d < now.date() else None))
        habits.append((h["name"], week))
    blocks = sorted(
        (Block(_hm(b["start"]), _hm(b["end"]), b["title"], b.get("focus", False)) for b in day.get("blocks", [])),
        key=lambda b: b.start,
    )
    return State(
        now=now,
        goals=[(g["text"], g.get("done", False)) for g in day.get("goals", [])],
        blocks=blocks,
        habits=habits[:3],
        day_start=_hm(raw.get("day_start", "08:00")),
        day_end=_hm(raw.get("day_end", "18:00")),
    )
