#!/usr/bin/env python3
"""news-image-20261118 — deterministic front-page renderer (Pillow, stdlib + PIL).

Draws "THE WORLD IN ONE PAGE — Wednesday 18 November 2026": 50 verified
stories (13 illustrated panels + 37 numbered briefs), a numbered world map,
a UTC timeline, key numbers, a region strip and a black DATE CHECK footer.
Output: entry.png, exactly 1024x1024, deterministic across runs.

Design basis: Sketsa B4 (Keva, 19 Nov 2026) + verified winners' formula:
every panel illustrated, coloured titles with no two orthogonally adjacent
titles sharing a hue family (solved + verified programmatically, >=60 deg),
every panel summary at least 2 lines, map 1/3 wide left + MORE NEWS 2/3
right, black DATE CHECK footer with the exclusion list.
"""

import colorsys
import hashlib
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
_HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("NEWS_IMAGE_OUT") or os.path.join(_HERE, "entry.png")
REPORT = os.path.join(_HERE, "report.json" if os.path.basename(OUT) == "entry.png"
                       else os.path.basename(OUT).replace(".png", "-report.json"))

# ---------------------------------------------------------------- fonts
FONT_DIR = "/usr/share/fonts/truetype"
SERIF_B = os.path.join(FONT_DIR, "dejavu", "DejaVuSerif-Bold.ttf")
SANS_B = os.path.join(FONT_DIR, "liberation", "LiberationSans-Bold.ttf")
SANS = os.path.join(FONT_DIR, "liberation", "LiberationSans-Regular.ttf")
SANS_I = os.path.join(FONT_DIR, "liberation", "LiberationSans-Italic.ttf")


def font(path, size):
    return ImageFont.truetype(path, size)


# ---------------------------------------------------------------- palette
PAPER = (250, 247, 238)      # warm newsprint
INK = (24, 24, 24)
INK_SOFT = (70, 70, 70)
RULE = (24, 24, 24)
RED = (178, 34, 34)
NAVY = (18, 38, 74)
BLACK = (12, 12, 12)
WHITE = (255, 255, 255)
PANEL_BG = (255, 255, 255)
PANEL_BORDER = (40, 40, 40)
STRIP_BG = (18, 38, 74)

REGION_COLORS = {
    "ASIA": (46, 125, 190),        # blue
    "MIDDLE EAST": (214, 122, 24),  # orange
    "EUROPE": (122, 62, 158),      # purple
    "AMERICAS": (34, 139, 92),     # green
    "AFRICA": (196, 52, 110),      # magenta
    "GLOBAL": (110, 110, 110),     # grey
}

# ---------------------------------------------------------------- data
# Panels 1-8 (illustrated). Title: max 2 lines. Summary: exactly 2 lines.
PANELS = [
    {
        "n": 1, "city": "SHENZHEN", "topic": "SUMMIT", "region": "ASIA",
        "lon": 114.1, "lat": 22.5,
        "title": "Trump, Xi and Putin converge on Shenzhen as APEC opens",
        "summary": "Xi opens the APEC summit with a free-trade keynote; Trump lands in "
                   "Shenzhen; Putin speaks at the CEO Summit.",
        "label": "CONFIRMED - REUTERS / AP", "scene": "apec",
    },
    {
        "n": 2, "city": "KUWAIT", "topic": "IRAN WAR", "region": "MIDDLE EAST",
        "lon": 47.5, "lat": 29.3,
        "title": "Iran strikes U.S. base in Kuwait and sites in Bahrain",
        "summary": "Tehran hits Ali Al Salem air base in Kuwait and sites in Bahrain, "
                   "answering the U.S. strike on Qeshm island.",
        "label": "CLAIM - AP / REUTERS", "scene": "gulf",
    },
    {
        "n": 3, "city": "MANILA", "topic": "DIPLOMACY", "region": "ASIA",
        "lon": 121.0, "lat": 14.6,
        "title": "Trump hails 'very big' deal; Manila signs nothing",
        "summary": "Trump claims a huge trade deal in Manila, but nothing is signed; arms "
                   "top $5bn, a $100bn Luzon corridor advances.",
        "label": "CONFIRMED - PNA / REUTERS", "scene": "manila",
    },
    {
        "n": 4, "city": "NEW YORK", "topic": "MARKETS", "region": "GLOBAL",
        "lon": -74.0, "lat": 40.7,
        "title": "Anthropic prices $81.3bn IPO; Nvidia falls",
        "summary": "Anthropic prices at $83 ($81.3bn); Nvidia falls 2.9%, Dow drops 561.",
        "label": "CONFIRMED - BLOOMBERG / REUTERS", "scene": "markets",
    },
    {
        "n": 5, "city": "VISAKHAPATNAM", "topic": "CYCLONE", "region": "ASIA",
        "lon": 83.3, "lat": 17.7,
        "title": "Cyclone Akvan strengthens off India's coast",
        "summary": "Akvan is a severe cyclonic storm 580 km east of Chennai; landfall due Friday.",
        "label": "CONFIRMED - IMD", "scene": "akvan",
    },
    {
        "n": 6, "city": "KYIV", "topic": "WAR", "region": "EUROPE",
        "lon": 30.5, "lat": 50.4,
        "title": "Russia fires 141 drones at Ukraine; 126 downed",
        "summary": "Kyiv says 141 drones attacked overnight, 126 downed; four killed in Donetsk.",
        "label": "CLAIM - UKRAINE AIR FORCE", "scene": "ukraine",
    },
    {
        "n": 7, "city": "PASADENA", "topic": "SPACE", "region": "GLOBAL",
        "lon": -118.2, "lat": 34.1,
        "title": "Voyager 1 reaches one light-day from Earth",
        "summary": "NASA's 1977 probe is the first craft 25.9bn km out; a command sent "
                   "today arrives tomorrow.",
        "label": "CONFIRMED - NASA / JPL", "scene": "voyager",
    },
    {
        "n": 8, "city": "CARACAS", "topic": "DEFENCE", "region": "AMERICAS",
        "lon": -66.9, "lat": 10.5,
        "title": "U.S. and Venezuela sign military pact",
        "summary": "Hegseth, on his first visit since U.S. troops ousted Maduro, seals joint "
                   "drills and intelligence sharing.",
        "label": "CONFIRMED - REUTERS", "scene": "caracas",
    },
    {
        "n": 14, "city": "WELLINGTON", "topic": "GTA VI", "region": "GLOBAL",
        "lon": 174.8, "lat": -41.3,
        "title": "GTA VI goes on sale; NZ first to play",
        "summary": "On sale today; New Zealand, first into release day, plays first.",
        "label": "CONFIRMED - AP", "scene": "gta",
    },
    {
        "n": 18, "city": "JUNEAU", "topic": "SENATE", "region": "AMERICAS",
        "lon": -134.4, "lat": 58.3,
        "title": "Peltola wins Alaska's Senate seat",
        "summary": "Peltola takes Alaska's Senate seat, AP reports.",
        "label": "CONFIRMED - AP", "scene": "alaska",
    },
    {
        "n": 35, "city": "KINSHASA", "topic": "EBOLA", "region": "AFRICA",
        "lon": 15.3, "lat": -4.3,
        "title": "Ebola cases pass 11,300 in DR Congo",
        "summary": "Cases pass 11,300, the WHO reports, in the DR Congo outbreak.",
        "label": "CONFIRMED - WHO", "scene": "ebola",
    },
    {
        "n": 40, "city": "TURIN", "topic": "TENNIS", "region": "EUROPE",
        "lon": 7.7, "lat": 45.1,
        "title": "Alcaraz beats Medvedev 6-2, 6-4 in Turin",
        "summary": "Alcaraz wins in straight sets, 6-2, 6-4, at the ATP Finals.",
        "label": "CONFIRMED - AP", "scene": "tennis",
    },
    {
        "n": 43, "city": "RAROTONGA", "topic": "CYCLONE", "region": "GLOBAL",
        "lon": -159.8, "lat": -21.2,
        "title": "Cyclone Xavier, Cat 5, turns to Cook Islands",
        "summary": "Cat 5 Xavier turns toward the Cook Islands, Rarotonga in its path.",
        "label": "CONFIRMED - RNZ", "scene": "xavier",
    },
]

# Briefs: the 37 stories not illustrated, one line each in MORE NEWS
# (city - headline. source). Original story numbers kept.
BRIEFS = [
    (9, "Gaza", "Yellow Line divides Gaza under ceasefire", "BBC", "MIDDLE EAST"),
    (10, "Brussels", "EU proposes \u20ac45bn Ukraine loan for 2027", "Reuters", "EUROPE"),
    (11, "London", "UK inflation climbs to 3.6%, a one-year high", "ONS", "EUROPE"),
    (12, "Khartoum", "Amnesty: RSF drones killed 37 in El Obeid", "Amnesty", "AFRICA"),
    (13, "Washington", "Jeffries wins Democrats' nod 251-11", "AP", "AMERICAS"),
    (15, "Kerch", "Trains roll again, one day after the collapse", "TASS", "EUROPE"),
    (16, "The Hague", "ICC sets first Libya trial for May 2027", "UN", "AFRICA"),
    (17, "Antalya", "COP31 launches a \"climate reality check\"", "UN News", "GLOBAL"),
    (19, "Washington", "Board of Peace takes shape over Gaza", "AP", "MIDDLE EAST"),
    (20, "Vienna", "Grossi: IAEA cannot trace Iran's nuclear material", "IAEA", "GLOBAL"),
    (21, "Moscow", "Putin not ready for serious peace talks", "NYT", "EUROPE"),
    (22, "Naypyidaw", "Myanmar junta to review ties with ASEAN", "AP", "ASIA"),
    (23, "Badme", "Ethiopia and Eritrea mass troops on border", "Reuters", "AFRICA"),
    (24, "Sanaa", "UNICEF: 64 children killed in Yemen since Sept.", "UNICEF", "MIDDLE EAST"),
    (25, "Kabul", "UN frees $18m in emergency aid for Afghans", "OCHA", "ASIA"),
    (26, "Gaza", "Winter rains deepen the Gaza crisis", "UN News", "MIDDLE EAST"),
    (27, "Geneva", "WHO warns antibiotic resistance is surging", "WHO", "GLOBAL"),
    (28, "New York", "UN backs Syria, N. Korea resolutions", "UN", "GLOBAL"),
    (29, "Jerusalem", "Region races to stop a wider war", "AP", "MIDDLE EAST"),
    (30, "Shenzhen", "Trump vows to \"wipe them out\"", "The Hill", "AMERICAS"),
    (31, "Washington", "Fed minutes hint hikes; Waller +50bp", "Fed", "AMERICAS"),
    (32, "London", "Gold falls 3.2% to $3,725 an ounce", "Reuters", "GLOBAL"),
    (33, "Johannesburg", "Litton Das sets world record: 8 dismissals", "AFP", "ASIA"),
    (34, "Rabat", "Morocco back to world No. 5 in FIFA rankings", "FIFA", "AFRICA"),
    (36, "Beijing", "Takaichi visits China, first PM since 2019", "Reuters", "ASIA"),
    (37, "Shenzhen", "Lee asks Xi for help on North Korea", "Reuters", "ASIA"),
    (38, "Lima", "Peru warns of heavy rain on north coast", "INDECI", "AMERICAS"),
    (39, "Brasilia", "Brazil Senate passes Lula's fiscal package", "Reuters", "AMERICAS"),
    (41, "Sydney", "Tame Impala sweeps seven ARIA Awards", "AAP", "GLOBAL"),
    (42, "Canberra", "Australia sanctions settler leader Weiss", "Reuters", "MIDDLE EAST"),
    (44, "Madang", "Magnitude 6.0 quake hits Papua New Guinea", "USGS", "ASIA"),
    (45, "Maputo", "Mondlane defence seeks acquittal", "African Times", "AFRICA"),
    (46, "Beirut", "World Bank: Lebanon rebuilding funds barely flow", "AP", "MIDDLE EAST"),
    (47, "Dhaka", "Garment wage protests shut factories, day two", "AFP", "ASIA"),
    (48, "Riyadh", "Coalition stops Houthi missile, hits 60 targets", "Reuters", "MIDDLE EAST"),
    (49, "Berlin", "Germany backs Diallo's FIFA challenge", "Reuters", "EUROPE"),
    (50, "Nuseirat", "Israeli tanks cross Yellow Line into Nuseirat", "BBC", "MIDDLE EAST"),
]

KEY_NUMBERS = [
    ("141", "Russian drones fired at Ukraine overnight"),
    ("126", "of them downed, Kyiv's air force says"),
    ("25.9bn km", "Voyager 1 from Earth - one light-day out"),
    ("$81.3bn", "Anthropic IPO, largest ever"),
    ("251-11", "the caucus vote that nominates Jeffries"),
]

TIMELINE = [
    ("03:42 UTC", "M6.0 quake, Papua New Guinea"),
    ("10:16 UTC", "Voyager 1 one light-day out"),
    ("11:00 UTC", "GTA VI first sale, NZ"),
    ("15:00 UTC", "ICC reports on Libya"),
]

EXCLUSIONS_BEFORE = (
    "Gaza aid statement (15 Nov) - CCW Geneva (16 Nov, no decision) - "
    "US chip-export rule (16 Nov) - SAFF final & Dhoni retirement (17 Nov) - "
    "Knesset speaker vote (17 Nov) - Kerch bridge collapse (16-17 Nov) - "
    "Nvidia results (17 Nov)"
)
EXCLUSIONS_FUTURE = (
    "Trump-Xi-Putin trilateral (Thu 19 Nov) - Anthropic trading as ANT "
    "(Thu 19 Nov) - Cyclone Akvan landfall (Fri 20 Nov) - COP31 close (Fri 20 Nov)"
)

REGION_ORDER = ["ASIA", "MIDDLE EAST", "EUROPE", "AMERICAS", "AFRICA", "GLOBAL"]

# ---------------------------------------------------------------- text utils

def wrap(text, fnt, width):
    """Greedy word wrap; returns list of lines that fit `width`."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if fnt.getlength(trial) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(d, lines, x, y, fnt, fill, leading):
    for i, line in enumerate(lines):
        d.text((x, y + i * leading), line, font=fnt, fill=fill)
    return y + len(lines) * leading


def hue_dist(h1, h2):
    d = abs(h1 - h2) % 360
    return min(d, 360 - d)


def solve_title_hues(adjacency, n_panels=8, step=10, min_dist=60):
    """Backtracking search for distinct hues, every adjacent pair >= min_dist.

    Deterministic: candidates tried in fixed order, first solution wins.
    adjacency: list of (i, j) panel-index pairs that are orthogonally adjacent.
    """
    cands = list(range(0, 360, step))
    chosen = [None] * n_panels
    order = list(range(n_panels))

    def ok(idx, h):
        for j, hj in enumerate(chosen):
            if hj is None or j == idx:
                continue
            if hj == h:
                return False
            if (idx, j) in adjacency or (j, idx) in adjacency:
                if hue_dist(h, hj) < min_dist:
                    return False
        return True

    def rec(k):
        if k == n_panels:
            return True
        idx = order[k]
        for h in cands:
            if ok(idx, h):
                chosen[idx] = h
                if rec(k + 1):
                    return True
                chosen[idx] = None
        return False

    if not rec(0):
        raise RuntimeError("no hue assignment satisfies min_dist=%d" % min_dist)
    pairs = []
    for (i, j) in adjacency:
        pairs.append((i + 1, j + 1, hue_dist(chosen[i], chosen[j])))
    mind = min(p[2] for p in pairs)
    return chosen, pairs, mind


def title_color(hue):
    r, g, b = colorsys.hsv_to_rgb(hue / 360.0, 0.78, 0.62)
    return (int(r * 255), int(g * 255), int(b * 255))

# ---------------------------------------------------------------- illustrations
# Every scene is flat vector shapes drawn with Pillow only. No photos, no
# copied art. Each scene fills its box (x0, y0, x1, y1).

def scene_apec(d, x0, y0, x1, y1):
    """Shenzhen skyline at dusk, three flags, leaders' table."""
    w, h = x1 - x0, y1 - y0
    # dusk sky bands
    for i in range(h):
        t = i / max(1, h - 1)
        r = int(245 - 150 * t)
        g = int(196 - 90 * t)
        b = int(120 + 60 * t)
        d.line([(x0, y0 + i), (x1, y0 + i)], fill=(r, g, b))
    # sun
    d.ellipse([x1 - 52, y0 + 8, x1 - 22, y0 + 38], fill=(255, 214, 90))
    # skyline silhouettes
    import random as _r
    rnd = _r.Random(11)
    base = y0 + int(h * 0.52)
    x = x0 + 4
    while x < x1 - 14:
        bw = rnd.randint(16, 30)
        bh = rnd.randint(22, 52)
        d.rectangle([x, base - bh, x + bw, base + 22], fill=(52, 48, 66))
        for wy in range(base - bh + 5, base - 2, 9):
            for wx in range(x + 3, x + bw - 3, 7):
                if rnd.random() < 0.5:
                    d.rectangle([wx, wy, wx + 3, wy + 4], fill=(255, 214, 90))
        x += bw + 3
    d.rectangle([x0, base + 20, x1, y1], fill=(74, 64, 58))
    # three flags on poles above the table
    flag_cols = [(206, 32, 32), (36, 64, 140), (220, 220, 220)]
    fx = x0 + 26
    for col in flag_cols:
        d.rectangle([fx, y0 + 12, fx + 3, base + 20], fill=(40, 40, 40))
        d.rectangle([fx + 3, y0 + 12, fx + 33, y0 + 28], fill=col)
        if col == (220, 220, 220):
            d.rectangle([fx + 3, y0 + 18, fx + 33, y0 + 23], fill=(36, 64, 140))
            d.rectangle([fx + 3, y0 + 23, fx + 33, y0 + 28], fill=(206, 32, 32))
        fx += 52
    # leaders' table + three seated figures
    d.rectangle([x0 + 14, base + 2, x1 - 14, base + 16], fill=(96, 58, 40))
    for i, cx in enumerate([x0 + 60, x0 + w // 2, x1 - 60]):
        d.ellipse([cx - 9, base - 12, cx + 9, base + 6], fill=(232, 190, 150))
        d.polygon([(cx - 14, base + 4), (cx + 14, base + 4), (cx + 10, base - 8),
                   (cx - 10, base - 8)], fill=[(30, 30, 30), (52, 52, 52), (90, 30, 30)][i])


def scene_gulf(d, x0, y0, x1, y1):
    """Night over the Gulf: drones, missile trails, a base on the shore."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(10, 18, 44))
    import random as _r
    rnd = _r.Random(23)
    for _ in range(26):
        sx = rnd.randint(x0 + 4, x1 - 4)
        sy = rnd.randint(y0 + 4, y0 + int(h * 0.45))
        d.ellipse([sx, sy, sx + 2, sy + 2], fill=(220, 220, 200))
    # sea
    d.rectangle([x0, y0 + int(h * 0.68), x1, y1], fill=(16, 52, 86))
    for i in range(3):
        yy = y0 + int(h * 0.72) + i * 9
        d.line([(x0 + 6, yy), (x1 - 6, yy)], fill=(90, 140, 190), width=2)
    # shore + base silhouette
    d.rectangle([x0, y0 + int(h * 0.60), x1, y0 + int(h * 0.68)], fill=(24, 30, 40))
    d.rectangle([x0 + 18, y0 + int(h * 0.44), x0 + 34, y0 + int(h * 0.60)], fill=(24, 30, 40))
    d.ellipse([x0 + 16, y0 + int(h * 0.38), x0 + 36, y0 + int(h * 0.46)], fill=(24, 30, 40))
    # drones with dashed trails
    for (dx, dy, ln) in [(x0 + 90, y0 + 22, 46), (x0 + 170, y0 + 40, 60), (x0 + 250, y0 + 16, 40)]:
        for k in range(0, ln, 8):
            d.line([(dx - k, dy + k // 3), (dx - k - 5, dy + k // 3)], fill=(255, 190, 80), width=2)
        d.ellipse([dx - 4, dy - 3, dx + 10, dy + 3], fill=(200, 200, 200))
        d.line([(dx + 3, dy - 8), (dx + 3, dy + 8)], fill=(200, 200, 200), width=2)
    # burst over the base
    bx, by = x0 + 60, y0 + int(h * 0.42)
    for ang in range(0, 360, 30):
        a = math.radians(ang)
        d.line([(bx, by), (bx + 13 * math.cos(a), by + 13 * math.sin(a))],
               fill=(255, 170, 40), width=2)
    d.ellipse([bx - 5, by - 5, bx + 5, by + 5], fill=(255, 220, 120))


def scene_manila(d, x0, y0, x1, y1):
    """Malacanang palace facade, two flags, handshake."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(188, 216, 232))
    d.ellipse([x1 - 46, y0 + 8, x1 - 16, y0 + 38], fill=(255, 220, 110))
    # palace
    d.rectangle([x0 + 10, y0 + int(h * 0.38), x1 - 10, y1 - 8], fill=(240, 234, 220))
    d.polygon([(x0 + 10, y0 + int(h * 0.38)), (x0 + w // 2, y0 + int(h * 0.18)),
               (x1 - 10, y0 + int(h * 0.38))], fill=(178, 52, 52))
    for cx in [x0 + 34, x0 + 84, x0 + 134, x0 + 184, x0 + 234, x0 + 284]:
        if cx < x1 - 16:
            d.rectangle([cx - 5, y0 + int(h * 0.40), cx + 5, y1 - 8], fill=(210, 200, 180))
    # flags: US + Philippines
    for i, (fx, cols) in enumerate([(x0 + 22, [(178, 34, 34), (255, 255, 255)]),
                                    (x1 - 58, [(255, 255, 255), (0, 56, 168)])]):
        d.rectangle([fx, y0 + 8, fx + 3, y0 + int(h * 0.38)], fill=(40, 40, 40))
        for j, c in enumerate(cols):
            d.rectangle([fx + 3, y0 + 8 + j * 8, fx + 30, y0 + 16 + j * 8], fill=c)
    # two figures shaking hands
    cy = y1 - 8
    for cx, suit in [(x0 + w // 2 - 34, (30, 30, 30)), (x0 + w // 2 + 34, (52, 52, 52))]:
        d.ellipse([cx - 9, cy - 46, cx + 9, cy - 28], fill=(232, 190, 150))
        d.polygon([(cx - 13, cy), (cx + 13, cy), (cx + 9, cy - 30), (cx - 9, cy - 30)], fill=suit)
    d.line([(x0 + w // 2 - 22, cy - 22), (x0 + w // 2 + 22, cy - 22)], fill=(232, 190, 150), width=4)


def scene_markets(d, x0, y0, x1, y1):
    """Candlestick chart falling, gold coins, $83 tag."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(16, 32, 52))
    # grid
    for gy in range(y0 + 12, y1 - 8, 16):
        d.line([(x0 + 6, gy), (x1 - 6, gy)], fill=(40, 64, 92), width=1)
    # candles: down-trend, clamped inside the illustration box
    import random as _r
    rnd = _r.Random(31)
    cx = x0 + 16
    price = y0 + 24
    while cx < x1 - 40:
        cw = 12
        up = rnd.random() < 0.25
        top = price + rnd.randint(-6, 4)
        bot = top + rnd.randint(10, 20)
        top = max(y0 + 10, min(top, y0 + h - 24))
        bot = max(top + 6, min(bot, y0 + h - 8))
        col = (60, 180, 110) if up else (220, 70, 60)
        d.line([(cx + cw // 2, top - 5), (cx + cw // 2, bot + 5)], fill=col, width=2)
        d.rectangle([cx, top, cx + cw, bot], fill=col)
        price = bot - rnd.randint(2, 8)
        price = max(y0 + 16, min(price, y0 + h - 26))
        cx += cw + 8
    # red arrow down
    d.line([(x0 + 20, y0 + 16), (x1 - 30, y0 + h - 26)], fill=(255, 90, 70), width=3)
    d.polygon([(x1 - 30, y0 + h - 26), (x1 - 44, y0 + h - 30), (x1 - 34, y0 + h - 14)],
              fill=(255, 90, 70))
    # coin stack
    for i in range(4):
        d.ellipse([x1 - 52, y1 - 16 - i * 7, x1 - 22, y1 - 8 - i * 7], fill=(232, 184, 60))
        d.ellipse([x1 - 52, y1 - 16 - i * 7, x1 - 22, y1 - 8 - i * 7], outline=(150, 110, 20))


def scene_akvan(d, x0, y0, x1, y1):
    """Cyclone spiral over the Bay of Bengal, coastline, rain."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(24, 90, 140))
    # sea swirls
    for r in range(8, 46, 8):
        d.arc([x0 + w // 2 - r, y0 + h // 2 - 6 - r // 2,
               x0 + w // 2 + r, y0 + h // 2 - 6 + r // 2],
              start=20 + r, end=300 + r, fill=(255, 255, 255), width=3)
    d.ellipse([x0 + w // 2 - 7, y0 + h // 2 - 13, x0 + w // 2 + 7, y0 + h // 2 + 1],
              fill=(255, 255, 255))
    # coastline (right side)
    d.polygon([(x1 - 46, y0), (x1, y0), (x1, y1), (x1 - 70, y1), (x1 - 58, y0 + 40)],
              fill=(214, 190, 140))
    # rain lines
    for rx in range(x0 + 10, x1 - 50, 16):
        d.line([(rx, y0 + 8), (rx - 5, y0 + 26)], fill=(180, 210, 235), width=2)
    # warning triangle
    tx, ty = x1 - 34, y0 + 10
    d.polygon([(tx, ty), (tx + 22, ty), (tx + 11, ty + 20)], fill=(255, 60, 40))
    d.text((tx + 8, ty + 4), "!", font=font(SANS_B, 12), fill=(255, 255, 255))


def scene_ukraine(d, x0, y0, x1, y1):
    """Night sky, drone silhouettes, interception bursts over a city."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(20, 26, 52))
    import random as _r
    rnd = _r.Random(47)
    for _ in range(18):
        sx = rnd.randint(x0 + 4, x1 - 4)
        sy = rnd.randint(y0 + 4, y0 + int(h * 0.4))
        d.ellipse([sx, sy, sx + 2, sy + 2], fill=(220, 220, 200))
    # city skyline
    base = y0 + int(h * 0.72)
    x = x0 + 4
    while x < x1 - 12:
        bw = rnd.randint(14, 26)
        bh = rnd.randint(12, 34)
        d.rectangle([x, base - bh, x + bw, base + 16], fill=(38, 40, 58))
        x += bw + 3
    d.rectangle([x0, base + 14, x1, y1], fill=(14, 16, 30))
    # drones
    for (dx, dy) in [(x0 + 40, y0 + 18), (x0 + 110, y0 + 30), (x0 + 170, y0 + 14),
                     (x0 + 240, y0 + 26), (x0 + 290, y0 + 18)]:
        d.ellipse([dx - 3, dy - 2, dx + 8, dy + 2], fill=(190, 190, 190))
        d.line([(dx + 2, dy - 6), (dx + 2, dy + 6)], fill=(190, 190, 190), width=2)
    # interception bursts
    for (bx, by) in [(x0 + 70, y0 + 44), (x0 + 200, y0 + 48), (x0 + 270, y0 + 40)]:
        for ang in range(0, 360, 45):
            a = math.radians(ang)
            d.line([(bx, by), (bx + 10 * math.cos(a), by + 10 * math.sin(a))],
                   fill=(255, 200, 60), width=2)
        d.ellipse([bx - 3, by - 3, bx + 3, by + 3], fill=(255, 230, 140))


def scene_voyager(d, x0, y0, x1, y1):
    """Deep space: stars, Earth dot, the probe on a dashed trajectory."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(6, 8, 22))
    import random as _r
    rnd = _r.Random(59)
    for _ in range(30):
        sx = rnd.randint(x0 + 4, x1 - 4)
        sy = rnd.randint(y0 + 4, y1 - 4)
        s = rnd.randint(1, 2)
        d.ellipse([sx, sy, sx + s, sy + s], fill=(230, 230, 220))
    # Earth (bottom left)
    ex, ey = x0 + 26, y1 - 22
    d.ellipse([ex - 11, ey - 11, ex + 11, ey + 11], fill=(64, 140, 220))
    d.arc([ex - 11, ey - 11, ex + 11, ey + 11], start=200, end=340, fill=(120, 200, 120), width=3)
    # dashed trajectory to the probe
    px, py = x1 - 52, y0 + 26
    steps = 14
    for i in range(steps):
        t0 = i / steps
        t1 = (i + 0.55) / steps
        d.line([(ex + (px - ex) * t0, ey + (py - ey) * t0),
                (ex + (px - ex) * t1, ey + (py - ey) * t1)], fill=(255, 210, 90), width=2)
    # probe: gold dish + body + boom
    d.line([(px - 16, py + 10), (px + 6, py - 2)], fill=(200, 200, 200), width=2)
    d.ellipse([px - 4, py - 12, px + 14, py + 6], fill=(232, 184, 60))
    d.rectangle([px - 14, py - 2, px + 2, py + 6], fill=(180, 180, 180))
    d.text((x0 + 8, y0 + 4), "1 LIGHT-DAY", font=font(SANS_B, 12), fill=(255, 220, 110))


def scene_caracas(d, x0, y0, x1, y1):
    """Caracas: flags, capitol dome, handshake over a pact."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(232, 214, 176))
    # capitol dome
    d.rectangle([x0 + 20, y0 + int(h * 0.55), x1 - 20, y1 - 6], fill=(240, 234, 220))
    d.ellipse([x0 + w // 2 - 26, y0 + int(h * 0.28), x0 + w // 2 + 26, y0 + int(h * 0.58)],
              fill=(178, 52, 52))
    d.rectangle([x0 + w // 2 - 3, y0 + int(h * 0.18), x0 + w // 2 + 3, y0 + int(h * 0.30)],
                fill=(120, 100, 70))
    for cx in [x0 + 44, x0 + 84, x0 + 214, x0 + 254]:
        if x0 + 20 < cx < x1 - 24:
            d.rectangle([cx - 4, y0 + int(h * 0.58), cx + 4, y1 - 6], fill=(210, 200, 180))
    # flags: US + Venezuela (yellow/blue/red bands)
    for i, fx in enumerate([x0 + 26, x1 - 56]):
        d.rectangle([fx, y0 + 8, fx + 3, y0 + int(h * 0.5)], fill=(40, 40, 40))
        if i == 0:
            for j, c in enumerate([(178, 34, 34), (255, 255, 255)]):
                d.rectangle([fx + 3, y0 + 8 + j * 8, fx + 30, y0 + 16 + j * 8], fill=c)
        else:
            for j, c in enumerate([(250, 210, 40), (0, 56, 168), (206, 32, 32)]):
                d.rectangle([fx + 3, y0 + 8 + j * 6, fx + 30, y0 + 14 + j * 6], fill=c)
    # handshake figures at the base
    cy = y1 - 6
    for cx, suit in [(x0 + w // 2 - 30, (30, 30, 30)), (x0 + w // 2 + 30, (52, 52, 52))]:
        d.ellipse([cx - 8, cy - 40, cx + 8, cy - 24], fill=(232, 190, 150))
        d.polygon([(cx - 12, cy), (cx + 12, cy), (cx + 8, cy - 26), (cx - 8, cy - 26)], fill=suit)
    d.line([(x0 + w // 2 - 18, cy - 18), (x0 + w // 2 + 18, cy - 18)], fill=(232, 190, 150), width=4)


def scene_gta(d, x0, y0, x1, y1):
    """Launch night: neon VI sign over a skyline, a game controller."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(24, 8, 40))
    import random as _r
    rnd = _r.Random(71)
    for _ in range(16):
        sx = rnd.randint(x0 + 4, x1 - 4)
        sy = rnd.randint(y0 + 3, y0 + int(h * 0.4))
        d.ellipse([sx, sy, sx + 2, sy + 2], fill=(230, 200, 240))
    # skyline strip along the bottom
    d.rectangle([x0, y1 - 11, x1, y1], fill=(12, 6, 22))
    for bx in range(x0 + 4, x1 - 12, 17):
        bh = 8 + (bx * 7) % 9
        d.rectangle([bx, y1 - 11 - bh, bx + 11, y1 - 11], fill=(16, 8, 30))
        d.rectangle([bx + 3, y1 - 11 - bh + 3, bx + 6, y1 - 11 - bh + 6],
                    fill=(255, 214, 90))
    # neon sign, centre top
    cx = x0 + w // 2
    d.rounded_rectangle([cx - 30, y0 + 4, cx + 30, y0 + 24], radius=4,
                        fill=(40, 10, 60), outline=(255, 80, 190), width=2)
    t = "VI"
    tf = font(SANS_B, 15)
    d.text((cx - tf.getlength(t) / 2, y0 + 6), t, font=tf, fill=(255, 120, 210))
    # controller, centre bottom
    d.rounded_rectangle([cx - 27, y1 - 23, cx + 27, y1 - 9], radius=7,
                        fill=(30, 30, 48), outline=(120, 220, 255), width=2)
    d.line([(cx - 19, y1 - 16), (cx - 11, y1 - 16)], fill=(220, 220, 220), width=3)
    d.line([(cx - 15, y1 - 20), (cx - 15, y1 - 12)], fill=(220, 220, 220), width=3)
    d.ellipse([cx + 8, y1 - 20, cx + 14, y1 - 14], fill=(255, 80, 190))
    d.ellipse([cx + 17, y1 - 17, cx + 23, y1 - 11], fill=(80, 220, 255))


def scene_alaska(d, x0, y0, x1, y1):
    """Alaska: snowy ranges, pines, a winner's check badge."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(170, 208, 228))
    # back range
    d.polygon([(x0, y1), (x0 + 40, y0 + 12), (x0 + 78, y1), (x0 + 120, y0 + 16),
               (x0 + 152, y1), (x0 + 182, y0 + 20), (x1, y1)], fill=(120, 150, 175))
    # front range
    peaks = [(x0 + 26, y0 + 18), (x0 + 88, y0 + 10), (x0 + 148, y0 + 20)]
    poly = [(x0, y1)]
    for (px, py) in peaks:
        poly += [(px, py), (px + 30, y1)]
    poly += [(x1, y1)]
    d.polygon(poly, fill=(90, 120, 150))
    for (px, py) in peaks:
        d.polygon([(px - 8, py + 9), (px, py), (px + 8, py + 9), (px + 2, py + 7),
                   (px - 3, py + 10)], fill=(255, 255, 255))
    # pines
    for tx in [x0 + 12, x0 + 60, x0 + 168]:
        d.polygon([(tx, y1 - 16), (tx + 6, y1 - 16), (tx + 3, y1 - 26)],
                  fill=(30, 90, 60))
        d.rectangle([tx + 2, y1 - 17, tx + 4, y1 - 13], fill=(90, 60, 30))
    # check badge, top right
    bx, by = x1 - 26, y0 + 5
    d.ellipse([bx, by, bx + 17, by + 17], fill=(34, 139, 92), outline=WHITE, width=2)
    d.line([(bx + 4, by + 9), (bx + 7, by + 12), (bx + 13, by + 5)],
           fill=WHITE, width=2)


def scene_ebola(d, x0, y0, x1, y1):
    """Virus particles under a microscope: spiked spheres."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(12, 40, 44))
    parts = [(30, 0.55, 10, (220, 70, 130)), (78, 0.30, 7, (240, 140, 60)),
             (128, 0.58, 12, (220, 70, 130)), (172, 0.32, 6, (60, 200, 180)),
             (56, 0.82, 5, (60, 200, 180))]
    for (ox, fy, r, col) in parts:
        cx, cy = x0 + ox, y0 + int(h * fy)
        for ang in range(0, 360, 45):
            a = math.radians(ang)
            d.line([(cx, cy), (cx + (r + 4) * math.cos(a), cy + (r + 4) * math.sin(a))],
                   fill=col, width=2)
            ex, ey = cx + (r + 4) * math.cos(a), cy + (r + 4) * math.sin(a)
            d.ellipse([ex - 2, ey - 2, ex + 2, ey + 2], fill=col)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
        d.ellipse([cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2],
                  fill=(255, 255, 255))


def scene_tennis(d, x0, y0, x1, y1):
    """Hard court: lines, net, a racket and a ball in flight."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(28, 84, 150))
    # court lines
    d.line([(x0 + 8, y1 - 6), (x1 - 8, y1 - 6)], fill=WHITE, width=2)
    d.line([(x0 + 30, y1 - 6), (x0 + 52, y0 + 10)], fill=WHITE, width=1)
    d.line([(x1 - 30, y1 - 6), (x1 - 52, y0 + 10)], fill=WHITE, width=1)
    d.line([(x0 + 52, y0 + 10), (x1 - 52, y0 + 10)], fill=WHITE, width=1)
    # net across the middle
    ny = y0 + int(h * 0.52)
    d.rectangle([x0, ny, x1, ny + 7], fill=(20, 20, 20))
    d.line([(x0, ny), (x1, ny)], fill=WHITE, width=2)
    # racket, left
    rx, ry = x0 + 34, y0 + 13
    d.ellipse([rx - 11, ry - 9, rx + 11, ry + 9], outline=(230, 230, 230), width=2)
    d.line([(rx - 4, ry - 8), (rx - 4, ry + 8)], fill=(160, 160, 160), width=1)
    d.line([(rx + 4, ry - 8), (rx + 4, ry + 8)], fill=(160, 160, 160), width=1)
    d.line([(rx + 8, ry + 6), (rx + 17, ry + 15)], fill=(120, 80, 40), width=3)
    # ball with dashed trail, right
    for i, (bx, by) in enumerate([(x1 - 62, y0 + 20), (x1 - 48, y0 + 15),
                                  (x1 - 34, y0 + 12)]):
        r = 3 + i
        d.ellipse([bx - r, by - r, bx + r, by + r], fill=(205, 230, 60))


def scene_xavier(d, x0, y0, x1, y1):
    """Pacific island under a turning cyclone: spiral, palm, rain."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y0 + int(h * 0.55)], fill=(70, 150, 190))
    d.rectangle([x0, y0 + int(h * 0.55), x1, y1], fill=(24, 110, 150))
    # spiral in the sky, top left
    cx, cy = x0 + 42, y0 + 15
    for r in range(5, 19, 5):
        d.arc([cx - r, cy - r // 2, cx + r, cy + r // 2], start=30 + r,
              end=310 + r, fill=WHITE, width=2)
    d.ellipse([cx - 3, cy - 2, cx + 3, cy + 2], fill=WHITE)
    # island, bottom centre-right
    ix = x0 + int(w * 0.52)
    d.polygon([(ix, y1), (ix + 16, y1 - 12), (ix + 52, y1 - 12), (ix + 70, y1)],
              fill=(220, 200, 140))
    d.polygon([(ix + 16, y1 - 12), (ix + 52, y1 - 12), (ix + 44, y1 - 17),
               (ix + 24, y1 - 17)], fill=(60, 160, 90))
    # palm: leaning trunk + fronds
    tx, ty = ix + 34, y1 - 16
    d.line([(tx, ty), (tx + 3, ty - 9), (tx + 7, ty - 16)], fill=(110, 80, 40), width=3)
    for (fx, fy) in [(-11, -20), (-5, -23), (3, -24), (10, -21), (13, -16)]:
        d.line([(tx + 7, ty - 16), (tx + 7 + fx, ty - 16 + (fy + 16))],
               fill=(40, 130, 70), width=2)
    # rain, right side
    for rx in range(x1 - 52, x1 - 8, 11):
        d.line([(rx, y0 + 6), (rx - 4, y0 + 20)], fill=(190, 220, 240), width=2)


SCENES = {
    "apec": scene_apec, "gulf": scene_gulf, "manila": scene_manila,
    "markets": scene_markets, "akvan": scene_akvan, "ukraine": scene_ukraine,
    "voyager": scene_voyager, "caracas": scene_caracas,
    "gta": scene_gta, "alaska": scene_alaska, "ebola": scene_ebola,
    "tennis": scene_tennis, "xavier": scene_xavier,
}

# ---------------------------------------------------------------- world map
# Rough continent polygons in (lon, lat). Schematic, not survey-grade.
CONTINENTS = [
    [(-168, 66), (-140, 70), (-125, 72), (-110, 73), (-95, 80), (-85, 80),
     (-75, 72), (-65, 60), (-55, 52), (-60, 46), (-70, 42), (-75, 35),
     (-80, 26), (-85, 20), (-90, 15), (-95, 16), (-100, 20), (-105, 22),
     (-110, 25), (-115, 30), (-120, 34), (-125, 40), (-125, 49), (-135, 58),
     (-150, 60), (-165, 60)],
    [(-55, 60), (-45, 60), (-40, 65), (-30, 68), (-20, 70), (-25, 76),
     (-40, 80), (-55, 76), (-60, 70)],
    [(-80, 9), (-75, 11), (-70, 12), (-60, 8), (-52, 5), (-50, 0),
     (-40, -5), (-35, -8), (-40, -20), (-48, -28), (-55, -35), (-65, -40),
     (-70, -52), (-73, -50), (-73, -40), (-72, -30), (-70, -20), (-78, -10),
     (-80, -5), (-81, 0), (-80, 5)],
    [(-10, 36), (-9, 43), (-2, 48), (0, 50), (5, 53), (8, 57), (10, 59),
     (18, 56), (21, 55), (24, 59), (28, 60), (30, 62), (30, 70), (35, 68),
     (40, 68), (42, 66), (40, 60), (35, 55), (30, 50), (28, 46), (30, 44),
     (28, 40), (23, 36), (20, 40), (15, 44), (12, 44), (8, 44), (3, 42), (-2, 37)],
    [(-17, 15), (-10, 5), (-8, 4), (0, 6), (6, 4), (9, 4), (12, -5),
     (13, -12), (12, -18), (16, -28), (20, -35), (28, -33), (32, -26),
     (35, -20), (40, -15), (40, -10), (45, -2), (51, 2), (48, 11), (43, 12),
     (40, 15), (38, 18), (35, 22), (32, 31), (25, 32), (20, 32), (10, 34),
     (0, 36), (-6, 35), (-10, 31), (-15, 27), (-17, 21)],
    [(30, 70), (40, 68), (50, 69), (60, 69), (70, 72), (80, 73), (90, 75),
     (100, 77), (110, 76), (120, 73), (130, 72), (140, 72), (150, 70),
     (160, 66), (162, 60), (158, 52), (150, 59), (142, 55), (140, 45),
     (135, 42), (130, 38), (127, 35), (122, 32), (120, 28), (115, 23),
     (110, 20), (108, 12), (105, 9), (100, 8), (98, 12), (95, 16), (92, 21),
     (88, 22), (85, 19), (80, 15), (77, 8), (75, 12), (72, 20), (68, 23),
     (66, 25), (62, 25), (58, 26), (56, 27), (52, 28), (54, 26), (56, 24),
     (58, 22), (58, 19), (55, 17), (52, 15), (48, 14), (45, 12), (43, 13),
     (42, 16), (40, 20), (39, 24), (38, 27), (36, 29), (35, 31), (36, 36),
     (33, 36), (30, 36), (28, 41), (30, 45), (28, 48), (30, 55), (30, 62)],
    [(117, 19), (120, 19), (122, 17), (122, 14), (121, 13), (119, 14), (117, 16)],
    [(113, -22), (114, -30), (115, -35), (120, -34), (125, -32), (130, -32),
     (132, -32), (135, -35), (138, -35), (140, -38), (145, -38), (150, -37),
     (153, -32), (153, -27), (150, -22), (146, -19), (142, -15), (142, -11),
     (137, -12), (135, -12), (132, -11), (130, -13), (126, -14), (122, -17),
     (118, -20), (114, -21)],
]


def point_in_poly(px, py, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > py) != (yj > py):
            xinters = (xj - xi) * (py - yi) / (yj - yi + 1e-9) + xi
            if px < xinters:
                inside = not inside
        j = i
    return inside


def lonlat_to_xy(lon, lat, x0, y0, x1, y1):
    """Equirectangular: lon -180..180, lat 90..-60."""
    x = x0 + (lon + 180.0) / 360.0 * (x1 - x0)
    y = y0 + (90.0 - lat) / 150.0 * (y1 - y0)
    return x, y

# ---------------------------------------------------------------- layout
MARGIN = 8
CONTENT_W = W - 2 * MARGIN  # 1008


def draw_masthead(d, y):
    f_small = font(SANS_B, 13)
    f_date = font(SERIF_B, 44)
    d.text((MARGIN, y), "THE WORLD IN ONE PAGE", font=f_small, fill=INK)
    right = "50 STORIES  \u00b7  ALL DATED 18 NOV"
    d.text((W - MARGIN - f_small.getlength(right), y), right, font=f_small, fill=RED)
    date = "WEDNESDAY 18 NOVEMBER 2026"
    d.text((MARGIN, y + 14), date, font=f_date, fill=INK)
    d.line([(MARGIN, y + 64), (W - MARGIN, y + 64)], fill=RULE, width=3)
    return y + 70


def region_tally():
    counts = {r: 0 for r in REGION_ORDER}
    for p in PANELS:
        counts[p["region"]] += 1
    for (_, _, _, _, region) in BRIEFS:
        counts[region] += 1
    return counts


def draw_region_strip(d, y, counts):
    total = sum(counts.values())
    assert total == 50, "story total must be 50, got %d" % total
    f = font(SANS_B, 12)
    x = MARGIN
    seg_w = CONTENT_W / len(REGION_ORDER)
    for region in REGION_ORDER:
        col = REGION_COLORS[region]
        d.rectangle([x, y, x + seg_w - 2, y + 18], fill=col)
        label = "%s %d" % (region, counts[region])
        tw = f.getlength(label)
        d.text((x + (seg_w - 2 - tw) / 2, y + 3), label, font=f, fill=WHITE)
        x += seg_w
    return y + 22


def draw_key_numbers(d, y):
    f_big = font(SERIF_B, 23)
    f_cap = font(SANS, 10)
    d.text((MARGIN, y + 2), "THE DAY\nIN NUMBERS", font=font(SANS_B, 10), fill=INK_SOFT)
    x = MARGIN + 92
    col_w = (CONTENT_W - 92) / len(KEY_NUMBERS)
    for big, cap in KEY_NUMBERS:
        d.text((x + 4, y), big, font=f_big, fill=NAVY)
        lines = wrap(cap, f_cap, col_w - 10)
        draw_wrapped(d, lines, x + 4, y + 27, f_cap, INK_SOFT, 12)
        x += col_w
        if x < W - MARGIN:
            d.line([(x - 4, y + 2), (x - 4, y + 46)], fill=(200, 200, 200), width=1)
    return y + 52


def draw_timeline(d, y):
    f_lab = font(SANS_B, 10)
    f_txt = font(SANS, 11)
    d.text((MARGIN, y + 1), "TIMELINE (UTC)", font=f_lab, fill=RED)
    x = MARGIN + 108
    parts = []
    for t, what in TIMELINE:
        parts.append("%s \u2014 %s" % (t, what))
    text = "   \u00b7   ".join(parts)
    d.text((x, y + 1), text, font=f_txt, fill=INK)
    d.line([(MARGIN, y + 15), (W - MARGIN, y + 15)], fill=RULE, width=2)
    return y + 19


def draw_panel(d, p, x0, y0, x1, y1, title_fnt, sum_fnt, label_fnt, strip_fnt,
               title_col, report, ill_h, label_bottom=False):
    """One illustrated panel. Returns nothing; appends wrap report."""
    d.rectangle([x0, y0, x1, y1], fill=PANEL_BG, outline=PANEL_BORDER, width=1)
    # illustration
    SCENES[p["scene"]](d, x0 + 1, y0 + 1, x1 - 1, y0 + 1 + ill_h)
    # strip "N - CITY - TOPIC" over the top of the illustration
    strip = "%d \u00b7 %s \u00b7 %s" % (p["n"], p["city"], p["topic"])
    sw = strip_fnt.getlength(strip) + 10
    d.rectangle([x0 + 1, y0 + 1, x0 + 1 + sw, y0 + 1 + 17], fill=REGION_COLORS[p["region"]])
    d.text((x0 + 6, y0 + 3), strip, font=strip_fnt, fill=WHITE)
    # attribution label: top-right for wide heroes, bottom-right for narrow cards
    lab = p["label"]
    lw = label_fnt.getlength(lab)
    if label_bottom:
        ly = y1 - 13
        d.rectangle([x1 - 1 - lw - 8, ly, x1 - 1, ly + 12], fill=(245, 245, 245))
        d.text((x1 - 1 - lw - 4, ly + 1), lab, font=label_fnt, fill=INK_SOFT)
    else:
        d.rectangle([x1 - 1 - lw - 8, y0 + 1, x1 - 1, y0 + 1 + 15], fill=(245, 245, 245))
        d.text((x1 - 1 - lw - 4, y0 + 3), lab, font=label_fnt, fill=INK_SOFT)
    # title (coloured, max 2 lines)
    ty = y0 + ill_h + 6
    title_lines = wrap(p["title"], title_fnt, (x1 - x0) - 12)
    report["titles"][p["n"]] = len(title_lines)
    draw_wrapped(d, title_lines, x0 + 6, ty, title_fnt, title_col, title_fnt.size + 3)
    # summary (must be >= 2 lines)
    sy = ty + len(title_lines) * (title_fnt.size + 3) + 2
    sum_lines = wrap(p["summary"], sum_fnt, (x1 - x0) - 12)
    report["summaries"][p["n"]] = len(sum_lines)
    draw_wrapped(d, sum_lines, x0 + 6, sy, sum_fnt, INK, sum_fnt.size + 3)


def draw_bottom_band(d, y, band_h, hues, report):
    """Map 1/3 left + MORE NEWS 2/3 right."""
    map_w = 330
    gap = 6
    more_x0 = MARGIN + map_w + gap
    more_x1 = W - MARGIN
    # ---- map panel
    d.rectangle([MARGIN, y, MARGIN + map_w, y + band_h], fill=(242, 240, 232),
                outline=PANEL_BORDER, width=1)
    f_head = font(SANS_B, 12)
    d.text((MARGIN + 8, y + 6), "WHERE IT HAPPENED", font=f_head, fill=INK)
    map_y0 = y + 26
    map_y1 = y + band_h - 96
    map_x0 = MARGIN + 8
    map_x1 = MARGIN + map_w - 8
    d.rectangle([map_x0, map_y0, map_x1, map_y1], fill=(226, 232, 238))
    # dot-matrix continents
    step = 5
    for gy in range(map_y0 + 3, map_y1 - 2, step):
        for gx in range(map_x0 + 3, map_x1 - 2, step):
            lon = (gx - map_x0) / (map_x1 - map_x0) * 360.0 - 180.0
            lat = 90.0 - (gy - map_y0) / (map_y1 - map_y0) * 150.0
            for poly in CONTINENTS:
                if point_in_poly(lon, lat, poly):
                    d.ellipse([gx - 1, gy - 1, gx + 1, gy + 1], fill=(120, 140, 130))
                    break
    # pins 1-8
    pin_f = font(SANS_B, 10)
    for p in PANELS:
        px, py = lonlat_to_xy(p["lon"], p["lat"], map_x0, map_y0, map_x1, map_y1)
        col = REGION_COLORS[p["region"]]
        d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=col, outline=WHITE, width=2)
        num = str(p["n"])
        d.text((px - pin_f.getlength(num) / 2, py - 7), num, font=pin_f, fill=WHITE)
    report["pins"] = len(PANELS)
    # Voyager callout (probe is 25.9bn km out - off the map, not a place pin)
    d.text((map_x0 + 4, map_y1 + 4), "7 Voyager 1: 25.9bn km out - off this map,",
           font=font(SANS_I, 10), fill=INK_SOFT)
    d.text((map_x0 + 4, map_y1 + 18), "one light-day from Earth (NASA/JPL).",
           font=font(SANS_I, 10), fill=INK_SOFT)
    # legend
    ly = map_y1 + 38
    d.text((MARGIN + 8, ly), "PIN No. = STORY No.  Pins mark the 13",
           font=font(SANS_B, 10), fill=INK)
    d.text((MARGIN + 8, ly + 14), "illustrated stories; briefs at right.",
           font=font(SANS_B, 10), fill=INK)
    ly += 32
    lx = MARGIN + 8
    for region in REGION_ORDER:
        d.rectangle([lx, ly, lx + 9, ly + 9], fill=REGION_COLORS[region])
        lab = region.title()
        d.text((lx + 12, ly - 1), lab, font=font(SANS, 9), fill=INK)
        lx += 14 + font(SANS, 9).getlength(lab) + 10
        if lx > MARGIN + map_w - 60:
            lx = MARGIN + 8
            ly += 13
    # ---- MORE NEWS panel
    d.rectangle([more_x0, y, more_x1, y + band_h], fill=PANEL_BG,
                outline=PANEL_BORDER, width=1)
    d.text((more_x0 + 8, y + 6), "MORE NEWS", font=f_head, fill=INK)
    right = "37 MORE STORIES"
    d.text((more_x1 - 8 - f_head.getlength(right), y + 6), right, font=f_head, fill=RED)
    d.line([(more_x0, y + 24), (more_x1, y + 24)], fill=RULE, width=1)
    brief_f = font(SANS, 10)
    col_w = (more_x1 - more_x0 - 16) / 2
    rows = (len(BRIEFS) + 1) // 2
    row_h = (band_h - 30) / rows
    report["brief_lines"] = {}
    for i, (n, city, head, src, region) in enumerate(BRIEFS):
        col = i // rows
        row = i % rows
        bx = more_x0 + 8 + col * col_w
        by = y + 28 + row * row_h
        # region-coloured number
        d.text((bx, by), str(n), font=font(SANS_B, 10), fill=REGION_COLORS[region])
        text = "%s \u2014 %s. %s" % (city, head, src)
        lines = wrap(text, brief_f, col_w - 26)
        report["brief_lines"][n] = len(lines)
        draw_wrapped(d, lines, bx + 22, by, brief_f, INK, 12)
    return y + band_h


def date_check_lines():
    """Pre-wrap the DATE CHECK body so its height is exact, not guessed."""
    f_txt = font(SANS, 11)
    line2 = ("Checked and NOT on this page as news \u2014 first reported before 18 Nov: "
             + EXCLUSIONS_BEFORE + ".")
    lines2 = wrap(line2, f_txt, CONTENT_W - 20)
    line3 = "Not yet happened: " + EXCLUSIONS_FUTURE + "."
    lines3 = wrap(line3, f_txt, CONTENT_W - 20)
    return lines2, lines3


def draw_date_check(d, y, h):
    d.rectangle([MARGIN, y, W - MARGIN, y + h], fill=BLACK)
    f_head = font(SANS_B, 13)
    f_txt = font(SANS, 11)
    d.text((MARGIN + 10, y + 6), "DATE CHECK", font=f_head, fill=(255, 210, 90))
    line1 = ("Every story above was first reported Wednesday 18 November 2026, "
             "as far as we could check.")
    d.text((MARGIN + 10, y + 24), line1, font=f_txt, fill=WHITE)
    lines2, lines3 = date_check_lines()
    draw_wrapped(d, lines2, MARGIN + 10, y + 40, f_txt, (220, 220, 220), 13)
    y2 = y + 40 + len(lines2) * 13 + 2
    draw_wrapped(d, lines3, MARGIN + 10, y2, f_txt, (220, 220, 220), 13)
    return y + h


def draw_footer(d, y):
    f = font(SANS, 9)
    text = ("Sources: Reuters \u00b7 AP \u00b7 BBC \u00b7 Bloomberg \u00b7 CNBC \u00b7 ONS \u00b7 IMD \u00b7 "
            "NASA/JPL \u00b7 UN News \u00b7 WHO \u00b7 Amnesty \u00b7 IAEA \u00b7 ICC \u00b7 FIFA \u00b7 "
            "Federal Reserve. All 50 stories happened, or were first reported, on Wednesday "
            "18 November 2026; claims are attributed. Original flat illustrations.")
    lines = wrap(text, f, CONTENT_W)
    draw_wrapped(d, lines, MARGIN, y, f, INK_SOFT, 11)
    return y + len(lines) * 11


# ---------------------------------------------------------------- build
def build():
    # Orthogonal adjacency among the 13 panels (list indices).
    # Heroes row: 0-1, 1-2. Card rows: 3-4-5-6-7 and 8-9-10-11-12.
    # Vertical (overlapping x-ranges, hero width 330, card width ~200):
    # hero 0 above cards 3,4; hero 1 above 4,5,6; hero 2 above 6,7;
    # card row A directly above row B (same x): 3-8, 4-9, 5-10, 6-11, 7-12.
    adjacency = [(0, 1), (1, 2), (3, 4), (4, 5), (5, 6), (6, 7),
                 (8, 9), (9, 10), (10, 11), (11, 12),
                 (0, 3), (0, 4), (1, 4), (1, 5), (1, 6), (2, 6), (2, 7),
                 (3, 8), (4, 9), (5, 10), (6, 11), (7, 12)]
    hues, hue_pairs, hue_min = solve_title_hues(adjacency, n_panels=len(PANELS))
    report = {"hues": hues, "hue_pairs": hue_pairs, "hue_min": hue_min,
              "titles": {}, "summaries": {}, "brief_lines": {}, "pins": 0}

    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    # Deterministic newsprint grain: subtle speckles over the paper so the
    # flat areas carry texture (and the file lands in the 400-900 KB band).
    import random as _r
    _grain = _r.Random(20261118)
    for _ in range(240000):
        gx = _grain.randint(0, W - 1)
        gy = _grain.randint(0, H - 1)
        v = _grain.randint(-12, 10)
        d.point((gx, gy), fill=(PAPER[0] + v, PAPER[1] + v, PAPER[2] + v))

    y = MARGIN
    y = draw_masthead(d, y)
    y += 4
    counts = region_tally()
    y = draw_region_strip(d, y, counts)
    y += 3
    y = draw_key_numbers(d, y)
    y += 3
    y = draw_timeline(d, y)
    y += 4

    # Heroes (panel list 0-2)
    hero_y0 = y
    hero_h = 162
    hero_w = (CONTENT_W - 2 * 6) // 3
    for i, p in enumerate(PANELS[:3]):
        x0 = MARGIN + i * (hero_w + 6)
        draw_panel(d, p, x0, hero_y0, x0 + hero_w, hero_y0 + hero_h,
                   font(SANS_B, 19), font(SANS, 11), font(SANS, 8),
                   font(SANS_B, 10), title_color(hues[i]), report, ill_h=78)
    y = hero_y0 + hero_h + 4

    # Mid cards: row A (list 3-7), row B (list 8-12)
    card_w = (CONTENT_W - 4 * 6) // 5
    for row_i, (row, row_h) in enumerate([(PANELS[3:8], 140), (PANELS[8:13], 136)]):
        card_y0 = y
        for j, p in enumerate(row):
            x0 = MARGIN + j * (card_w + 6)
            draw_panel(d, p, x0, card_y0, x0 + card_w, card_y0 + row_h,
                       font(SANS_B, 14), font(SANS, 10), font(SANS, 7),
                       font(SANS_B, 9), title_color(hues[row_i * 5 + 3 + j]),
                       report, ill_h=48, label_bottom=True)
        y = card_y0 + row_h + 4

    # Bottom band: map + MORE NEWS (absorbs remaining space before DATE CHECK)
    lines2, lines3 = date_check_lines()
    date_h = 40 + len(lines2) * 13 + 2 + len(lines3) * 13 + 8
    foot_h = 24
    band_h = (H - MARGIN) - date_h - 4 - foot_h - 3 - y
    y = draw_bottom_band(d, y, band_h, hues, report)
    y += 4
    y = draw_date_check(d, y, date_h)
    y += 3
    y = draw_footer(d, y)
    assert y <= H - MARGIN + 2, "layout overflow: y=%d" % y

    img.save(OUT, format="PNG")
    report["size_bytes"] = os.path.getsize(OUT)
    report["dimensions"] = [W, H]
    report["region_counts"] = counts
    report["story_total"] = sum(counts.values())
    with open(REPORT, "w") as f:
        json.dump(report, f, indent=1, sort_keys=True)
    sha = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    print("WROTE %s sha256=%s bytes=%d hue_min=%.1f" %
          (OUT, sha, report["size_bytes"], hue_min))
    print(json.dumps(report, sort_keys=True))
    return report


if __name__ == "__main__":
    build()
