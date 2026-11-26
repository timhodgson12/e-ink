"""Renders the daily-goals dashboard as a native 800x480 1-bit image.

The output image is exactly what gets pushed to the panel.

Screen selection (approved design 2026-11-26, direction A + weather dock):
    morning  – before day_start: the day ahead, nothing ticking yet
    evening  – at/after day_end: wrap-up with done/carry-forward verdicts
    empty    – no goals and no blocks all day
    alldone  – every goal ticked while the day still runs
    between  – a gap between blocks: the next block gets a countdown
    day      – the main view; carries the weather dock when weather is known
"""
import math
from datetime import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .state import State, Weather

W, H = 800, 480
BLACK, WHITE = 0, 255
FONT_DIR = Path(__file__).parent / "fonts"

M = 36        # outer margin, tuned for the stand's chin
SPLIT = 520   # left content | right timeline
GUTTER = 28   # clear of the split rule
DOCK_TOP = 416  # with the weather dock the timeline ends here; dock band 416..480


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / f"Ubuntu-{weight}.ttf"), size)


def to_1bit(img: Image.Image) -> Image.Image:
    # Drawn anti-aliased in greyscale then thresholded: keeps true font
    # weights, which FreeType's mono hinter thins out.
    return img.point(lambda p: 255 if p > 165 else 0).convert("1")


def mins(t: time) -> int:
    return t.hour * 60 + t.minute


def hatch(d: ImageDraw.ImageDraw, box, step=4):
    """Diagonal hatch fill: the only 'grey' a 1-bit panel can show cleanly."""
    x0, y0, x1, y1 = box
    for k in range(-(y1 - y0), x1 - x0, step):
        xa, ya = x0 + k, y1
        xb, yb = x0 + k + (y1 - y0), y0
        if xa < x0:
            ya -= x0 - xa
            xa = x0
        if xb > x1:
            yb += xb - x1
            xb = x1
        d.line([xa, ya, xb, yb], fill=BLACK)


def fit(d, text, fnt, max_w):
    if d.textlength(text, font=fnt) <= max_w:
        return text
    while text and d.textlength(text + "…", font=fnt) > max_w:
        text = text[:-1]
    return text.rstrip() + "…"


# ── Shared pieces ─────────────────────────────────────────────────────────────

def draw_header(d: ImageDraw.ImageDraw, s: State) -> None:
    d.text((M, 22), s.now.strftime("%A").upper(), font=font("B", 26), fill=BLACK)
    d.text((M, 56), s.now.strftime("%-d %B"), font=font("M", 20), fill=BLACK)
    clock = s.now.strftime("%H:%M")
    cf = font("B", 44)
    cw = d.textlength(clock, font=cf)
    d.text((SPLIT - GUTTER - cw, 26), clock, font=cf, fill=BLACK)
    d.line([M, 92, SPLIT - GUTTER, 92], fill=BLACK, width=3)


def draw_now(d: ImageDraw.ImageDraw, s: State, y: int) -> int:
    now_m = mins(s.now.time())
    cur = next((b for b in s.blocks if mins(b.start) <= now_m < mins(b.end)), None)
    nxt = next((b for b in s.blocks if mins(b.start) > now_m), None)
    inner = SPLIT - GUTTER - M

    d.text((M, y), "NOW", font=font("B", 16), fill=BLACK)
    if cur is None:
        d.text((M, y + 26), "Free until " + (nxt.start.strftime("%H:%M") if nxt else s.day_end.strftime("%H:%M")),
               font=font("B", 40), fill=BLACK)
        if nxt:
            d.text((M, y + 78), fit(d, f"Next  {nxt.start:%H:%M}  {nxt.title}", font("M", 20), inner),
                   font=font("M", 20), fill=BLACK)
        return y + 112

    left = mins(cur.end) - now_m
    span = f"{cur.start:%H:%M}–{cur.end:%H:%M}"
    d.text((M + 56, y - 2), span, font=font("M", 19), fill=BLACK)

    # largest size that keeps the title on one line; floor at 34
    for size in (52, 46, 40, 34):
        tf = font("B", size)
        if d.textlength(cur.title, font=tf) <= inner:
            break
    d.text((M, y + 24), fit(d, cur.title, tf, inner), font=tf, fill=BLACK)

    # progress bar with the minutes-left label beside it
    by = y + 96
    bx0, bx1 = M, SPLIT - GUTTER - 118
    d.rectangle([bx0, by, bx1, by + 18], outline=BLACK, width=2)
    frac = (now_m - mins(cur.start)) / max(1, mins(cur.end) - mins(cur.start))
    d.rectangle([bx0, by, bx0 + int((bx1 - bx0) * frac), by + 18], fill=BLACK)
    d.text((bx1 + 14, by - 3), f"{left} min left", font=font("B", 24), fill=BLACK)

    if nxt:
        d.text((M, by + 34), fit(d, f"Then  {nxt.start:%H:%M}  {nxt.title}", font("M", 19), inner),
               font=font("M", 19), fill=BLACK)
        return by + 62
    return by + 34


def draw_goals(d: ImageDraw.ImageDraw, s: State, y: int) -> int:
    inner = SPLIT - GUTTER - M
    done = sum(1 for _, ok in s.goals if ok)
    total = len(s.goals)
    d.text((M, y), "TODAY", font=font("B", 16), fill=BLACK)
    cnt = f"{done} of {total} done" if total else "no goals"
    cf = font("M", 16)
    d.text((SPLIT - GUTTER - d.textlength(cnt, font=cf), y + 1), cnt, font=cf, fill=BLACK)
    d.line([M, y + 24, SPLIT - GUTTER, y + 24], fill=BLACK, width=1)
    gy = y + 34
    gf = font("M", 26)
    show = s.goals[:3]
    for text, ok in show:
        d.rectangle([M, gy + 4, M + 26, gy + 29], outline=BLACK, width=2)
        label = fit(d, text, gf, inner - 42)
        d.text((M + 40, gy), label, font=gf, fill=BLACK)
        if ok:
            d.line([M + 6, gy + 16, M + 11, gy + 22, M + 22, gy + 8], fill=BLACK, width=3)
            tw = d.textlength(label, font=gf)
            d.line([M + 38, gy + 16, M + 40 + tw, gy + 16], fill=BLACK, width=2)
        gy += 42
    extra = total - len(show)
    if extra > 0:
        more = f"+{extra} more"
        d.text((SPLIT - GUTTER - d.textlength(more, font=font("M", 16)), y + 22), more,
               font=font("M", 16), fill=BLACK)
    return gy


def draw_habits(d: ImageDraw.ImageDraw, s: State, y: int) -> None:
    col = (SPLIT - GUTTER - M) // max(1, len(s.habits))
    d.line([M, y - 14, SPLIT - GUTTER, y - 14], fill=BLACK, width=1)
    for i, (name, week) in enumerate(s.habits):
        x0 = M + i * col
        d.text((x0, y), fit(d, name.upper(), font("B", 14), col - 14), font=font("B", 14), fill=BLACK)
        for j, v in enumerate(week):
            cx, cy = x0 + 9 + j * 20, y + 30
            if v is True:
                d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=BLACK)
            elif v is False:
                d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], outline=BLACK, width=1)
                d.line([cx - 3, cy, cx + 3, cy], fill=BLACK)
            else:
                d.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=BLACK)
            if j == s.now.weekday():
                d.line([cx - 7, cy + 11, cx + 7, cy + 11], fill=BLACK, width=2)


def draw_timeline(d: ImageDraw.ImageDraw, s: State, bottom: int = H - 26) -> None:
    d.line([SPLIT, 0, SPLIT, H], fill=BLACK, width=3)
    tx0, tx1 = SPLIT + 58, W - M
    ty0, ty1 = 26, bottom
    t0, t1 = mins(s.day_start), mins(s.day_end)
    now_m = mins(s.now.time())

    def ypos(m):
        m = min(max(m, t0), t1)
        return ty0 + round((m - t0) / max(1, t1 - t0) * (ty1 - ty0))

    for h in range(s.day_start.hour, s.day_end.hour + 1):
        yy = ypos(h * 60)
        d.text((SPLIT + 12, yy - 9), f"{h:02d}", font=font("M", 15), fill=BLACK)
        for x in range(SPLIT + 40, tx1, 7):  # dotted hour line
            d.point((x, yy), fill=BLACK)

    for b in s.blocks:
        if mins(b.end) <= t0 or mins(b.start) >= t1 or mins(b.end) <= mins(b.start):
            continue
        y0, y1 = ypos(mins(b.start)) + 2, ypos(mins(b.end)) - 2
        past = mins(b.end) <= now_m
        cur = mins(b.start) <= now_m < mins(b.end)
        short = y1 - y0 < 26
        tf = font("M", 14 if short else 16)
        ly = y0 + ((y1 - y0 - 16) // 2 if short else 5)
        label = fit(d, b.title, tf, tx1 - tx0 - 16)
        if cur:
            d.rectangle([tx0, y0, tx1, y1], outline=BLACK, width=4)
            if b.focus and y1 - y0 >= 24:
                d.rectangle([tx0 + 5, y0 + 4, tx1 - 5, y1 - 5], fill=BLACK)
                tf2 = font("M", 15)
                d.text((tx0 + 14, ly), fit(d, b.title, tf2, tx1 - tx0 - 28), font=tf2, fill=WHITE)
            else:
                d.text((tx0 + 12, ly), label, font=tf, fill=BLACK)
        elif past:
            d.rectangle([tx0, y0, tx1, y1], outline=BLACK, width=1)
            hatch(d, (tx0 + 1, y0 + 1, tx1 - 1, y1 - 1), step=7)
            tw = d.textlength(label, font=tf)
            plate_y1 = max(y0 + 3, min(y0 + 24, y1 - 3))
            d.rectangle([tx0 + 4, y0 + 3, tx0 + 12 + tw, plate_y1], fill=WHITE)
            d.text((tx0 + 8, ly), label, font=tf, fill=BLACK)
        else:
            d.rectangle([tx0, y0, tx1, y1], outline=BLACK, width=2)
            d.text((tx0 + 8, ly), label, font=tf, fill=BLACK)

    if t0 <= now_m <= t1:  # now marker: triangle + rule across the column
        yn = ypos(now_m)
        d.polygon([(SPLIT + 38, yn - 8), (SPLIT + 52, yn), (SPLIT + 38, yn + 8)], fill=BLACK)
        d.rectangle([SPLIT + 52, yn - 1, tx1 + 6, yn + 1], fill=BLACK)
        d.rectangle([SPLIT + 52, yn - 4, tx1 + 6, yn - 2], fill=WHITE)
        d.rectangle([SPLIT + 52, yn + 2, tx1 + 6, yn + 4], fill=WHITE)


# ── Weather dock (bottom-right, under the timeline) ──────────────────────────

def _ico_sun(d, cx, cy, r=9):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=BLACK, width=2)
    for k in range(8):
        a = math.pi / 4 * k
        x0, y0 = cx + (r + 3) * math.cos(a), cy + (r + 3) * math.sin(a)
        x1, y1 = cx + (r + 7) * math.cos(a), cy + (r + 7) * math.sin(a)
        d.line([x0, y0, x1, y1], fill=BLACK, width=2)


def _cloud_shape(d, cx, cy, scale=1.0):
    """Filled cloud silhouette, flat-ish base. (~34x20 px at scale 1)"""
    s = scale
    d.ellipse([cx - 17 * s, cy - 4 * s, cx + 3 * s, cy + 12 * s], fill=BLACK)
    d.ellipse([cx - 8 * s, cy - 13 * s, cx + 12 * s, cy + 7 * s], fill=BLACK)
    d.rectangle([cx - 12 * s, cy + 2 * s, cx + 10 * s, cy + 10 * s], fill=BLACK)


def _ico_part(d, cx, cy):
    """Sun peeking top-left behind a cloud."""
    _ico_sun(d, cx - 8, cy - 8, r=7)
    # white plate under the cloud so the sun's rays read as 'behind'
    d.rectangle([cx - 10, cy - 2, cx + 16, cy + 12], fill=WHITE)
    _cloud_shape(d, cx + 2, cy + 1)


def _ico_rain(d, cx, cy):
    _cloud_shape(d, cx, cy - 5)
    for dx in (-9, 0, 9):
        x = cx + dx
        d.line([x, cy + 6, x - 3, cy + 14], fill=BLACK, width=2)


def _ico_drizzle(d, cx, cy):
    _cloud_shape(d, cx, cy - 5)
    for dx in (-10, -2, 6):
        x = cx + dx
        d.line([x, cy + 7, x - 1, cy + 11], fill=BLACK, width=2)
        d.line([x + 3, cy + 11, x + 2, cy + 15], fill=BLACK, width=2)


ICONS = {"sun": _ico_sun, "part": _ico_part, "cloud": _cloud_shape, "rain": _ico_rain, "drizzle": _ico_drizzle}


def draw_dock(d: ImageDraw.ImageDraw, wx: Weather) -> None:
    x0 = SPLIT + 4
    d.line([SPLIT, DOCK_TOP + 4, W - M, DOCK_TOP + 4], fill=BLACK, width=2)
    y = DOCK_TOP + 14
    ICONS[wx.icon](d, x0 + 20, y + 10)
    tx = x0 + 52
    d.text((tx, y - 2), f"{wx.hi}° / {wx.lo}°", font=font("B", 30), fill=BLACK)
    tx += d.textlength("888° / 888°", font=font("B", 30)) + 6
    rain = f"rain {wx.rain}%" if wx.rain else "dry"
    d.text((tx, y + 8), rain, font=font("M", 19), fill=BLACK)
    if wx.note:
        d.text((x0 + 2, y + 36), fit(d, wx.note, font("M", 16), W - M - x0 - 4), font=font("M", 16), fill=BLACK)


# ── State screens ─────────────────────────────────────────────────────────────

def _frame(d: ImageDraw.ImageDraw, title: str, sub: str) -> None:
    """Shared chrome for the big-title states: weekday, title, rule."""
    d.text((M, 22), sub, font=font("B", 26), fill=BLACK)
    d.text((M, 64), title, font=font("B", 64), fill=BLACK)
    d.line([M, 152, SPLIT - GUTTER, 152], fill=BLACK, width=3)


def _render_between(s: State) -> Image.Image:
    """Gap between blocks: the next thing IS the now, so it gets the big slot."""
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    now_m = mins(s.now.time())
    nxt = next((b for b in s.blocks if mins(b.start) > now_m), None)

    draw_header(d, s)
    d.text((M, 108), "NOW", font=font("B", 16), fill=BLACK)
    d.text((M, 134), "Free — no block scheduled", font=font("B", 40), fill=BLACK)
    y = 196
    if nxt:
        gap = mins(nxt.start) - now_m
        d.text((M, y), f"Next: {nxt.title}"[:36], font=font("B", 30), fill=BLACK)
        bf = font("B", 72)
        mins_txt = f"{gap} min"
        d.text((M, y + 44), mins_txt, font=bf, fill=BLACK)
        nw = d.textlength(mins_txt, font=bf)
        d.text((M + nw + 16, y + 44 + 36), f"until {nxt.start:%H:%M}", font=font("B", 26), fill=BLACK)
        d.text((M + nw + 16, y + 44 + 8), "gap of", font=font("M", 20), fill=BLACK)
        y += 44 + 88
    y = max(y + 6, 176)
    draw_goals(d, s, y)
    draw_habits(d, s, H - 56)
    draw_timeline(d, s)
    return to_1bit(img)


def _render_evening(s: State) -> Image.Image:
    """After day_end: the day, closed. Done/not-done, no 'you should be...'."""
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    now_m = mins(s.now.time())
    _frame(d, "Day closed", s.now.strftime("%A").upper())

    y = 176
    d.text((M, y), "GOALS", font=font("B", 16), fill=BLACK)
    done = sum(1 for _, ok in s.goals if ok)
    d.text((SPLIT - GUTTER - 60, y), f"{done} of {len(s.goals)}", font=font("B", 16), fill=BLACK)
    y += 30
    gf = font("M", 27)
    for text, ok in s.goals[:5]:
        d.rectangle([M, y + 4, M + 26, y + 29], outline=BLACK, width=2)
        label = fit(d, text, gf, SPLIT - GUTTER - M - 42 - 100)
        d.text((M + 40, y), label, font=gf, fill=BLACK)
        if ok:
            d.line([M + 6, y + 16, M + 11, y + 22, M + 22, y + 8], fill=BLACK, width=3)
            tw = d.textlength(label, font=gf)
            d.line([M + 38, y + 16, M + 40 + tw, y + 16], fill=BLACK, width=2)
        else:
            verdict = "carry fwd"
            vw = d.textlength(verdict, font=font("M", 18))
            d.text((SPLIT - GUTTER - 8 - vw, y + 8), verdict, font=font("M", 18), fill=BLACK)
        y += 44

    by = y + 16
    d.text((M, by), "TIME", font=font("B", 16), fill=BLACK)
    t0, t1 = mins(s.day_start), mins(s.day_end)
    worked = sum(min(mins(b.end), t1, now_m) - max(mins(b.start), t0)
                 for b in s.blocks
                 if mins(b.end) > t0 and mins(b.start) < min(t1, now_m) and mins(b.end) > mins(b.start))
    d.text((M + 64, by + 1), f"{worked // 60}h{worked % 60:02d} in blocks", font=font("M", 18), fill=BLACK)

    draw_habits(d, s, H - 56)
    draw_timeline(d, s)  # the day as it actually went, all past
    return to_1bit(img)


def _render_morning(s: State) -> Image.Image:
    """Before day_start: today's shape, nothing ticking yet."""
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    _frame(d, "Day starts " + s.day_start.strftime("%H:%M"), s.now.strftime("%A").upper())
    draw_goals(d, s, 176)
    d.line([M, 176 + 3 * 42 + 46, SPLIT - GUTTER, 176 + 3 * 42 + 46], fill=BLACK, width=1)
    draw_habits(d, s, H - 56)
    draw_timeline(d, s)
    return to_1bit(img)


def _render_empty(s: State) -> Image.Image:
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    draw_header(d, s)
    d.text((M, 120), "Nothing planned", font=font("B", 54), fill=BLACK)
    d.text((M, 190), "No goals, no blocks. Enjoy it or add some", font=font("M", 22), fill=BLACK)
    d.text((M, 220), "to data/goals.toml.", font=font("M", 22), fill=BLACK)
    draw_habits(d, s, H - 56)
    draw_timeline(d, s)
    return to_1bit(img)


def _render_alldone(s: State) -> Image.Image:
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    draw_header(d, s)
    d.text((M, 120), "All done", font=font("B", 72), fill=BLACK)
    nxt = next((b for b in s.blocks if mins(b.start) > mins(s.now.time())), None)
    if nxt:
        d.text((M, 216), fit(d, f"Next: {nxt.start:%H:%M} {nxt.title}", font("M", 24), SPLIT - GUTTER - M),
               font=font("M", 24), fill=BLACK)
    draw_habits(d, s, H - 56)
    draw_timeline(d, s)
    return to_1bit(img)


def _render_day(s: State, wx: Weather | None) -> Image.Image:
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    draw_header(d, s)
    y = draw_now(d, s, 108)
    y = max(y + 6, 262)
    draw_goals(d, s, y)
    draw_habits(d, s, H - 56)
    draw_timeline(d, s, DOCK_TOP - 8 if wx else H - 26)
    if wx:
        draw_dock(d, wx)
    return to_1bit(img)


# ── Entry points ──────────────────────────────────────────────────────────────

def render(s: State, wx: Weather | None = None) -> Image.Image:
    """Pick the screen that matches the moment, then draw it."""
    if s.now.time() < s.day_start:
        return _render_morning(s)
    if s.now.time() >= s.day_end:
        return _render_evening(s)
    if not s.goals and not s.blocks:
        return _render_empty(s)
    if s.goals and all(ok for _, ok in s.goals):
        return _render_alldone(s)
    now_m = mins(s.now.time())
    if not any(mins(b.start) <= now_m < mins(b.end) for b in s.blocks):
        return _render_between(s)
    return _render_day(s, wx)


def render_error(message: str) -> Image.Image:
    """Shown on the panel when the data file can't be read, so a typo is visible."""
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    d.text((M, 60), "CAN'T READ GOALS FILE", font=font("B", 40), fill=BLACK)
    d.line([M, 124, W - M, 124], fill=BLACK, width=2)
    y = 148
    for paragraph in message.split("\n"):
        line = ""
        for word in paragraph.split():
            if d.textlength(f"{line} {word}", font=font("M", 22)) > W - 2 * M:
                d.text((M, y), line, font=font("M", 22), fill=BLACK)
                y += 30
                line = word
            else:
                line = f"{line} {word}".strip()
        d.text((M, y), line, font=font("M", 22), fill=BLACK)
        y += 30
    d.text((M, H - 60), "Fix data/goals.toml — screen returns on its own.", font=font("M", 20), fill=BLACK)
    return to_1bit(img)
