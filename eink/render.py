"""Renders the daily-goals dashboard as a native 800x480 1-bit image.

The output image is exactly what gets pushed to the panel.
"""
from datetime import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .state import State

W, H = 800, 480
BLACK, WHITE = 0, 255
FONT_DIR = Path(__file__).parent / "fonts"


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / f"Ubuntu-{weight}.ttf"), size)


def to_1bit(img: Image.Image) -> Image.Image:
    # Drawn anti-aliased in greyscale then thresholded: keeps true font
    # weights, which FreeType's mono hinter thins out.
    return img.point(lambda p: 255 if p > 165 else 0).convert("1")


def render_error(message: str) -> Image.Image:
    """Shown on the panel when the data file can't be read, so a typo is visible."""
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    d.text((24, 24), "CAN'T READ GOALS FILE", font=font("B", 30), fill=BLACK)
    y, line = 80, ""
    for word in message.split():
        if d.textlength(f"{line} {word}", font=font("R", 20)) > W - 48:
            d.text((24, y), line, font=font("R", 20), fill=BLACK)
            y, line = y + 28, word
        else:
            line = f"{line} {word}".strip()
    d.text((24, y), line, font=font("R", 20), fill=BLACK)
    return to_1bit(img)


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


def render(s: State) -> Image.Image:
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    M = 24  # outer margin
    SPLIT = 532  # left content | right timeline
    now_m = mins(s.now.time())

    # ── Header ────────────────────────────────────────────────────────────
    d.text((M, 16), s.now.strftime("%A").upper(), font=font("B", 30), fill=BLACK)
    d.text((M, 52), s.now.strftime("%-d %B · week %V"), font=font("R", 18), fill=BLACK)
    clock = s.now.strftime("%H:%M")
    cf = font("B", 54)
    d.text((SPLIT - 20 - d.textlength(clock, font=cf), 12), clock, font=cf, fill=BLACK)
    d.line([M, 86, SPLIT - 20, 86], fill=BLACK, width=2)

    # ── Now ───────────────────────────────────────────────────────────────
    cur = next((b for b in s.blocks if mins(b.start) <= now_m < mins(b.end)), None)
    nxt = next((b for b in s.blocks if mins(b.start) > now_m), None)
    y = 100
    d.text((M, y), "NOW", font=font("B", 15), fill=BLACK)
    inner_w = SPLIT - 20 - M
    if cur:
        left = mins(cur.end) - now_m
        span = f"{cur.start:%H:%M}–{cur.end:%H:%M}"
        d.text((M + 48, y), span, font=font("R", 15), fill=BLACK)
        d.text((M, y + 22), fit(d, cur.title, font("B", 34), inner_w), font=font("B", 34), fill=BLACK)
        # progress bar: solid = elapsed
        bx0, by0, bx1, by1 = M, y + 72, SPLIT - 120, y + 92
        frac = (now_m - mins(cur.start)) / max(1, mins(cur.end) - mins(cur.start))
        d.rectangle([bx0, by0, bx1, by1], outline=BLACK, width=2)
        d.rectangle([bx0, by0, bx0 + int((bx1 - bx0) * frac), by1], fill=BLACK)
        lbl = f"{left} min left"
        d.text((SPLIT - 20 - d.textlength(lbl, font=font("M", 18)), by0 - 1), lbl, font=font("M", 18), fill=BLACK)
    else:
        d.text((M, y + 22), "Unscheduled", font=font("B", 34), fill=BLACK)
    if nxt:
        d.text((M, y + 104), fit(d, f"Next  {nxt.start:%H:%M}  {nxt.title}", font("R", 18), inner_w),
               font=font("R", 18), fill=BLACK)
    d.line([M, 236, SPLIT - 20, 236], fill=BLACK, width=1)

    # ── Today's three ─────────────────────────────────────────────────────
    y = 248
    done = sum(1 for _, ok in s.goals if ok)
    d.text((M, y), "TODAY'S THREE", font=font("B", 15), fill=BLACK)
    cnt = f"{done}/{len(s.goals)}"
    d.text((SPLIT - 20 - d.textlength(cnt, font=font("B", 15)), y), cnt, font=font("B", 15), fill=BLACK)
    gy = y + 28
    gf = font("M", 24)
    if not s.goals:
        d.text((M, gy), "No goals set for today", font=font("R", 24), fill=BLACK)
    extra = len(s.goals) - 3
    if extra > 0:
        more = f"+{extra} more"
        d.text((SPLIT - 70 - d.textlength(more, font=font("R", 15)), y), more, font=font("R", 15), fill=BLACK)
    for text, ok in s.goals[:3]:
        d.rectangle([M, gy + 3, M + 24, gy + 27], outline=BLACK, width=2)
        label = fit(d, text, gf, inner_w - 40)
        d.text((M + 38, gy), label, font=gf, fill=BLACK)
        if ok:
            d.line([M + 5, gy + 15, M + 10, gy + 21, M + 20, gy + 8], fill=BLACK, width=3)
            tw = d.textlength(label, font=gf)
            d.line([M + 36, gy + 17, M + 40 + tw, gy + 17], fill=BLACK, width=2)
        gy += 40

    # ── Habits (week grid) ────────────────────────────────────────────────
    d.line([M, 400, SPLIT - 20, 400], fill=BLACK, width=1)
    hy = 410
    col_w = (inner_w) // max(1, len(s.habits))
    for i, (name, week) in enumerate(s.habits):
        hx = M + i * col_w
        d.text((hx, hy), fit(d, name.upper(), font("B", 13), col_w - 12), font=font("B", 13), fill=BLACK)
        for j, v in enumerate(week):
            cx, cy = hx + 8 + j * 21, hy + 34
            today = j == s.now.weekday()
            if v is True:
                d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=BLACK)
            elif v is False:
                d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], outline=BLACK, width=1)
                d.line([cx - 3, cy, cx + 3, cy], fill=BLACK)
            else:
                d.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=BLACK)
            if today:
                d.line([cx - 7, cy + 12, cx + 7, cy + 12], fill=BLACK, width=2)

    # ── Timeline (right column) ───────────────────────────────────────────
    d.line([SPLIT, 0, SPLIT, H], fill=BLACK, width=2)
    tx0, tx1 = SPLIT + 56, W - M
    ty0, ty1 = 24, H - 24
    t0, t1 = mins(s.day_start), mins(s.day_end)

    def ypos(m):
        m = min(max(m, t0), t1)
        return ty0 + round((m - t0) / max(1, t1 - t0) * (ty1 - ty0))

    hf = font("R", 14)
    for h in range(s.day_start.hour, s.day_end.hour + 1):
        yy = ypos(h * 60)
        d.text((SPLIT + 12, yy - 8), f"{h:02d}", font=hf, fill=BLACK)
        for x in range(SPLIT + 36, tx1, 6):  # dotted hour line
            d.point((x, yy), fill=BLACK)
    for b in s.blocks:
        if mins(b.end) <= t0 or mins(b.start) >= t1 or mins(b.end) <= mins(b.start):
            continue
        y0, y1 = ypos(mins(b.start)) + 2, ypos(mins(b.end)) - 2
        if y1 - y0 < 12:  # too short to label legibly
            d.rectangle([tx0, y0, tx1, y1], fill=BLACK if b.focus else WHITE, outline=BLACK)
            continue
        past = mins(b.end) <= now_m
        short = y1 - y0 < 26
        tf = font("M", 13 if short else 15)
        ly = y0 + ((y1 - y0 - 15) // 2 if short else 4)
        label = fit(d, b.title, tf, tx1 - tx0 - 16)
        if b.focus and not past:
            d.rectangle([tx0, y0, tx1, y1], fill=BLACK)
            d.text((tx0 + 8, ly), label, font=tf, fill=WHITE)
        else:
            d.rectangle([tx0, y0, tx1, y1], fill=WHITE, outline=BLACK, width=2 if not past else 1)
            if past:
                hatch(d, (tx0 + 1, y0 + 1, tx1 - 1, y1 - 1), step=6)
                tw = d.textlength(label, font=tf)
                d.rectangle([tx0 + 4, y0 + 3, tx0 + 12 + tw, min(y0 + 23, y1 - 3)], fill=WHITE)
            d.text((tx0 + 8, ly), label, font=tf, fill=BLACK)
    if t0 <= now_m <= t1:  # now marker: triangle + rule across the column
        yn = ypos(now_m)
        d.polygon([(SPLIT + 36, yn - 7), (SPLIT + 48, yn), (SPLIT + 36, yn + 7)], fill=BLACK)
        d.rectangle([SPLIT + 48, yn - 1, tx1 + 8, yn + 1], fill=BLACK)
        d.rectangle([SPLIT + 48, yn - 3, tx1 + 8, yn - 2], fill=WHITE)
        d.rectangle([SPLIT + 48, yn + 2, tx1 + 8, yn + 3], fill=WHITE)
    return to_1bit(img)


def render_error(message: str) -> Image.Image:
    """Shown on the panel when the data file can't be read, so a typo is visible."""
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    d.text((24, 24), "CAN'T READ GOALS FILE", font=font("B", 30), fill=BLACK)
    y, line = 80, ""
    for word in message.split():
        if d.textlength(f"{line} {word}", font=font("R", 20)) > W - 48:
            d.text((24, y), line, font=font("R", 20), fill=BLACK)
            y, line = y + 28, word
        else:
            line = f"{line} {word}".strip()
    d.text((24, y), line, font=font("R", 20), fill=BLACK)
    return to_1bit(img)

