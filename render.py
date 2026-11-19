#!/usr/bin/env python3
"""news-image-20261118 — deterministic front-page renderer (Pillow, stdlib + PIL).

Draws "THE WORLD IN ONE PAGE — Wednesday 18 November 2026": 46 verified
stories (13 illustrated panels + 33 numbered briefs), a numbered world map,
a UTC timeline, key numbers, a region strip and a black DATE CHECK footer.
Output: entry.png, exactly 1024x1024, deterministic across runs.

Design basis: Sketsa B4 (Keva, 19 Nov 2026) + verified winners' formula,
revised for v5 after the dev-defeat analysis of v4 (ANALISIS-KEKALAHAN-V4.md
+ AUDIT-VISUAL-V4.md): 13 BIG panels (the dev #1 formula: 40 stories,
13 panels) with tall, INFORMATIVE scenes that tell each story (objects
specific to the event + in-scene labels, never a bare pictogram); the 3
softest panels (GTA VI, COP31, tennis) demoted to briefs so all 46 stories
stay; ONE serif family (Liberation Serif) for masthead, headlines,
summaries and briefs, sans only for labels/status/timeline/map/DATE CHECK;
panel strips cream with a small region-colour number chip + navy text;
brief numbers in a single dark red; region colours desaturated 20% with
equalised lightness and one consistent mapping everywhere (region bar =
panel chip = map pin); status as a dark chip with white text; briefs in
serif with bold city lead-ins, one line each; DATE CHECK itemised
per date (every exclusion listed with its own date, like dev #10);
map landmass darker, pins larger.
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
# v5: ONE serif family (Liberation Serif) for masthead + headlines +
# summaries + briefs; Liberation Sans only for labels, status chips,
# timeline, map captions and the DATE CHECK body.
FONT_DIR = "/usr/share/fonts/truetype"
SERIF_B = os.path.join(FONT_DIR, "liberation", "LiberationSerif-Bold.ttf")
SERIF = os.path.join(FONT_DIR, "liberation", "LiberationSerif-Regular.ttf")
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

BRIEF_RED = (155, 28, 28)    # #9B1C1C — the single brief-number colour
STRIP_CREAM = (252, 249, 240)


def _calm(rgb, sat_keep=0.8, light=0.42):
    """Desaturate a region colour and pin its lightness, so the six
    region colours sit at one visual weight (audit fix: colour harmony)."""
    h, l, s = colorsys.rgb_to_hls(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    r, g, b = colorsys.hls_to_rgb(h, light, s * sat_keep)
    return (int(r * 255), int(g * 255), int(b * 255))


REGION_COLORS = {
    "ASIA": _calm((46, 125, 190)),        # blue
    "MIDDLE EAST": _calm((214, 122, 24)),  # orange
    "EUROPE": _calm((122, 62, 158)),      # purple
    "AMERICAS": _calm((34, 139, 92)),     # green
    "AFRICA": _calm((196, 52, 110)),      # magenta
    "GLOBAL": (104, 104, 104),            # grey
}

# ---------------------------------------------------------------- data
# Illustrated panels, in reading order: 3 heroes, card row A (5),
# card row B (5) = 13 panels (v5: the 3 softest v4 panels — GTA VI,
# COP31, tennis — are briefs now, so every panel is hard news and big).
# Title: max 2 lines. Summary: >= 2 lines.
# The "n" literals below are placeholders: sequential numbers 1-16 in
# reading order are assigned after BRIEFS (see the renumbering block).
PANELS = [
    {
        "n": 1, "city": "SHENZHEN", "topic": "SUMMIT", "region": "ASIA",
        "lon": 114.1, "lat": 22.5,
        "title": "Xi opens APEC in Shenzhen as Trump lands",
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
        "title": "Akvan strengthens off India's coast",
        "summary": "Akvan is a severe cyclonic storm 580 km east of Chennai; landfall due Friday.",
        "label": "CONFIRMED - IMD", "scene": "akvan",
    },
    {
        "n": 6, "city": "KYIV", "topic": "WAR", "region": "EUROPE",
        "lon": 30.5, "lat": 50.4,
        "title": "Ukraine: 141 drones fired, 126 downed",
        "summary": "Kyiv says 141 drones attacked overnight, 126 downed; four killed in Donetsk.",
        "label": "CLAIM - UKRAINE AIR FORCE", "scene": "ukraine",
    },
    {
        "n": 7, "city": "PASADENA", "topic": "SPACE", "region": "GLOBAL",
        "lon": -118.2, "lat": 34.1,
        "title": "Voyager 1 reaches one light-day from Earth",
        "summary": "NASA's 1977 probe, first craft 25.9bn km out; signals take a day.",
        "label": "CONFIRMED - NASA / JPL", "scene": "voyager",
    },
    {
        "n": 8, "city": "CARACAS", "topic": "DEFENCE", "region": "AMERICAS",
        "lon": -66.9, "lat": 10.5,
        "title": "U.S. and Venezuela sign military pact",
        "summary": "Hegseth seals joint drills and intel sharing on first visit since Maduro fell.",
        "label": "CONFIRMED - REUTERS", "scene": "caracas",
    },
    {
        "n": 9, "city": "BRUSSELS", "topic": "EU LOAN", "region": "EUROPE",
        "lon": 4.35, "lat": 50.85,
        "title": "EU proposes \u20ac45bn Ukraine loan for 2027",
        "summary": "Brussels proposes a \u20ac45bn loan to support Ukraine through 2027.",
        "label": "CONFIRMED - REUTERS", "scene": "euloan",
    },
    {
        "n": 10, "city": "WASHINGTON", "topic": "FED", "region": "AMERICAS",
        "lon": -77.0, "lat": 38.9,
        "title": "Fed minutes hint hikes; Waller +50bp",
        "summary": "The Fed's minutes hint at rate hikes; Waller floats a 50bp rise.",
        "label": "CONFIRMED - FEDERAL RESERVE", "scene": "fed",
    },
    {
        "n": 11, "city": "LONDON", "topic": "INFLATION", "region": "EUROPE",
        "lon": -0.13, "lat": 51.5,
        "title": "UK inflation climbs to 3.6%",
        "summary": "UK inflation climbed to 3.6%, a one-year high, the ONS reported.",
        "label": "CONFIRMED - ONS", "scene": "ukinfl",
    },
    {
        "n": 14, "city": "KINSHASA", "topic": "EBOLA", "region": "AFRICA",
        "lon": 15.3, "lat": -4.3,
        "title": "Ebola cases pass 11,300 in DR Congo",
        "summary": "Cases pass 11,300, the WHO reports, in the DR Congo outbreak.",
        "label": "CONFIRMED - WHO", "scene": "ebola",
    },
    {
        "n": 16, "city": "RAROTONGA", "topic": "CYCLONE", "region": "GLOBAL",
        "lon": -159.8, "lat": -21.2,
        "title": "Xavier, Cat 5, turns to Cook Islands",
        "summary": "Cat 5 Xavier turns toward the Cook Islands, Rarotonga in its path.",
        "label": "CONFIRMED - RNZ", "scene": "xavier",
    },
]

# Briefs: the stories not illustrated, one line each in MORE NEWS
# (city - headline. source). Numbered sequentially after the panels
# by the renumbering block below.
BRIEFS = [
    (0, "Gaza", "Yellow Line divides Gaza under ceasefire", "BBC", "MIDDLE EAST"),
    (0, "Khartoum", "RSF drones killed 37 in El Obeid", "Amnesty", "AFRICA"),
    (0, "Washington", "Jeffries wins Democrats' nod 251-11", "AP", "AMERICAS"),
    (0, "The Hague", "ICC sets Libya trial for May 2027", "UN", "AFRICA"),
    (0, "Washington", "Board of Peace takes shape over Gaza", "AP", "MIDDLE EAST"),
    (0, "Vienna", "Grossi: Iran nuclear material untraced", "IAEA", "GLOBAL"),
    (0, "Moscow", "Putin not ready for peace talks", "NYT", "EUROPE"),
    (0, "Naypyidaw", "Junta to review ties with ASEAN", "AP", "ASIA"),
    (0, "Badme", "Ethiopia, Eritrea mass troops", "Reuters", "AFRICA"),
    (0, "Sanaa", "UNICEF: 64 children killed in Yemen", "UNICEF", "MIDDLE EAST"),
    (0, "Kabul", "UN frees $18m in aid for Afghans", "OCHA", "ASIA"),
    (0, "Gaza", "Winter rains deepen the Gaza crisis", "UN News", "MIDDLE EAST"),
    (0, "Geneva", "WHO: antibiotic resistance surging", "WHO", "GLOBAL"),
    (0, "Antalya", "COP31's climate reality check", "UN News", "GLOBAL"),
    (0, "New York", "UN backs Syria, N. Korea resolutions", "UN", "GLOBAL"),
    (0, "Jerusalem", "Region races to stop a wider war", "AP", "MIDDLE EAST"),
    (0, "Shenzhen", "Trump vows to \"wipe them out\"", "The Hill", "AMERICAS"),
    (0, "Wellington", "GTA VI goes on sale; NZ first to play", "AP", "GLOBAL"),
    (0, "London", "Gold falls 3.2% to $3,725 an ounce", "Reuters", "GLOBAL"),
    (0, "Rabat", "Morocco back to world No. 5 in FIFA", "FIFA", "AFRICA"),
    (0, "Beijing", "Takaichi in China, first PM since 2019", "Reuters", "ASIA"),
    (0, "Shenzhen", "Lee asks Xi for help on North Korea", "Reuters", "ASIA"),
    (0, "Lima", "Peru warns of heavy rain, north coast", "INDECI", "AMERICAS"),
    (0, "Brasilia", "Brazil Senate passes Lula fiscal plan", "Reuters", "AMERICAS"),
    (0, "Canberra", "Australia sanctions settler Weiss", "Reuters", "MIDDLE EAST"),
    (0, "Madang", "Magnitude 6.0 quake, Papua New Guinea", "USGS", "ASIA"),
    (0, "Maputo", "Mondlane defence seeks acquittal", "African Times", "AFRICA"),
    (0, "Beirut", "Lebanon rebuild funds barely flow", "AP", "MIDDLE EAST"),
    (0, "Dhaka", "Garment protests shut factories, day 2", "AFP", "ASIA"),
    (0, "Riyadh", "Coalition stops Houthi missile", "Reuters", "MIDDLE EAST"),
    (0, "Berlin", "Germany backs Diallo FIFA challenge", "Reuters", "EUROPE"),
    (0, "Turin", "Alcaraz beats Medvedev 6-2, 6-4", "AP", "EUROPE"),
    (0, "Nuseirat", "Israeli tanks cross Yellow Line", "BBC", "MIDDLE EAST"),
]

# Sequential numbering: illustrated panels are 1-13 in reading order
# (heroes, then card rows); briefs continue 14..N. Every number on the
# page (panel strips, map pins, MORE NEWS) uses these.
for _i, _p in enumerate(PANELS):
    _p["n"] = _i + 1
BRIEFS = [(len(PANELS) + 1 + _i, _c, _h, _s, _r)
          for _i, (_n, _c, _h, _s, _r) in enumerate(BRIEFS)]
STORY_TOTAL = len(PANELS) + len(BRIEFS)

KEY_NUMBERS = [
    ("141", "Russian drones fired at Ukraine overnight"),
    ("\u20ac45bn", "EU loan proposed for Ukraine, for 2027"),
    ("3.6%", "UK inflation - a one-year high (ONS)"),
    ("25.9bn km", "Voyager 1 from Earth - one light-day out"),
    ("$81.3bn", "Anthropic IPO, largest ever"),
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
    "Nvidia results (17 Nov) - Alaska Senate call (17 Nov)"
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

def _flag_star(d, cx, cy, r, col):
    """One filled 5-point star (deterministic geometry)."""
    pts = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rad = r if k % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    d.polygon(pts, fill=col)


def scene_apec(d, x0, y0, x1, y1):
    """Shenzhen skyline at dusk; three big flags (China, U.S., Russia) flying
    clear in the upper half. V3 redraw (Keva): no figures, no table band,
    flags whole and clear of the panel strip and label."""
    w, h = x1 - x0, y1 - y0
    # dusk sky bands
    for i in range(h):
        t = i / max(1, h - 1)
        d.line([(x0, y0 + i), (x1, y0 + i)],
               fill=(int(246 - 120 * t), int(198 - 70 * t), int(128 + 40 * t)))
    # flagpoles first; the skyline will overlap their feet
    poles = [x0 + 46, x0 + 152, x0 + 252]
    for px in poles:
        d.rectangle([px, y0 + 20, px + 3, y1 - 4], fill=(38, 36, 44))
        d.ellipse([px - 1, y0 + 17, px + 4, y0 + 22], fill=(250, 200, 80))
    # skyline silhouette along the bottom
    import random as _r
    rnd = _r.Random(11)
    ground = y1 - 10
    x = x0 + 3
    while x < x1 - 12:
        bw = rnd.randint(15, 28)
        bh = rnd.randint(13, 27)
        d.rectangle([x, ground - bh, x + bw, ground], fill=(52, 48, 66))
        for wy in range(ground - bh + 4, ground - 3, 8):
            for wx in range(x + 3, x + bw - 3, 6):
                if rnd.random() < 0.45:
                    d.rectangle([wx, wy, wx + 2, wy + 3], fill=(255, 214, 90))
        x += bw + 3
    d.rectangle([x0, ground, x1, y1], fill=(70, 60, 54))
    # tarmac foreground: dark apron with a dashed white centreline and a
    # yellow edge line, in front of the skyline (v5: the hero scene must
    # read as an airport arrival, not flags over rooftops)
    d.rectangle([x0, y1 - 13, x1, y1], fill=(44, 44, 52))
    for tx in range(x0 + 8, x1 - 14, 22):
        d.rectangle([tx, y1 - 8, tx + 12, y1 - 6], fill=(240, 240, 240))
    d.line([(x0, y1 - 13), (x1, y1 - 13)], fill=(250, 200, 80), width=2)
    # Flags: whole cloth right of each pole, tops below the strip/label
    # (y0+24), drawn last so nothing covers them. The right third of each
    # flag is shaded darker to read as a fold in the cloth.
    fy0, fy1 = y0 + 24, y0 + 24 + max(26, int(h * 0.34))
    fw = 58

    def bands(px, spec):
        split = px + 4 + int(fw * 0.68)
        for (f0, f1, col) in spec:
            ya = fy0 + int((fy1 - fy0) * f0)
            yb = fy0 + int((fy1 - fy0) * f1)
            d.rectangle([px + 4, ya, split, yb], fill=col)
            d.rectangle([split, ya, px + 4 + fw, yb],
                        fill=(int(col[0] * 0.8), int(col[1] * 0.8),
                              int(col[2] * 0.8)))
    # China: red field, one large star + four small stars
    bands(poles[0], [(0.0, 1.0, (206, 32, 32))])
    _flag_star(d, poles[0] + 14, fy0 + 8, 5, (255, 222, 60))
    for (sx, sy) in [(24, 4), (27, 9), (27, 15), (24, 20)]:
        _flag_star(d, poles[0] + sx, fy0 + sy, 2, (255, 222, 60))
    # United States: seven stripes + blue canton with dot stars
    bands(poles[1], [(i / 7.0, (i + 1) / 7.0,
                      (178, 34, 34) if i % 2 == 0 else (245, 245, 245))
                     for i in range(7)])
    d.rectangle([poles[1] + 4, fy0, poles[1] + 31, fy0 + 13], fill=(36, 52, 120))
    for ry in range(3):
        for rx in range(4):
            sx = poles[1] + 8 + rx * 6
            sy = fy0 + 3 + ry * 4
            d.rectangle([sx, sy, sx + 1, sy + 1], fill=(255, 255, 255))
    # Russia: white / blue / red horizontal bands
    bands(poles[2], [(0.0, 1 / 3.0, (245, 245, 245)),
                     (1 / 3.0, 2 / 3.0, (36, 64, 160)),
                     (2 / 3.0, 1.0, (206, 32, 32))])


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
    for (dx, dy, ln) in [(x0 + 90, y0 + 28, 46), (x0 + 170, y0 + 40, 60), (x0 + 244, y0 + 27, 40)]:
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
    # sun centred (clear of both flags); the palace roof overlaps its base
    d.ellipse([x0 + w // 2 - 14, y0 + 3, x0 + w // 2 + 14, y0 + 31],
              fill=(255, 220, 110))
    # palace
    d.rectangle([x0 + 10, y0 + int(h * 0.38), x1 - 10, y1 - 8], fill=(240, 234, 220))
    d.polygon([(x0 + 10, y0 + int(h * 0.38)), (x0 + w // 2, y0 + int(h * 0.18)),
               (x1 - 10, y0 + int(h * 0.38))], fill=(178, 52, 52))
    for cx in [x0 + 34, x0 + 84, x0 + 134, x0 + 184, x0 + 234, x0 + 284]:
        if cx < x1 - 16:
            d.rectangle([cx - 5, y0 + int(h * 0.40), cx + 5, y1 - 8], fill=(210, 200, 180))
    # flags: US + Philippines, lowered in v3 so the strip and label
    # rectangles no longer cover them
    for i, (fx, cols) in enumerate([(x0 + 22, [(178, 34, 34), (255, 255, 255)]),
                                    (x1 - 58, [(255, 255, 255), (0, 56, 168)])]):
        d.rectangle([fx, y0 + 21, fx + 3, y0 + 40], fill=(40, 40, 40))
        for j, c in enumerate(cols):
            d.rectangle([fx + 3, y0 + 21 + j * 8, fx + 30, y0 + 29 + j * 8], fill=c)
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
    """Cyclone Akvan over the Bay of Bengal: spiral, a track arrow curving
    in toward the Indian coast, surf on the shoreline, rain (v5: the scene
    must tell the landfall story, not just show a swirl)."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(24, 90, 140))
    # sea swirls
    cx, cy = x0 + w // 2 - 14, y0 + h // 2 - 4
    for r in range(8, 46, 8):
        d.arc([cx - r, cy - r // 2, cx + r, cy + r // 2],
              start=20 + r, end=300 + r, fill=(255, 255, 255), width=3)
    d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=(255, 255, 255))
    # coastline (right side)
    d.polygon([(x1 - 46, y0), (x1, y0), (x1, y1), (x1 - 70, y1), (x1 - 58, y0 + 40)],
              fill=(214, 190, 140))
    # surf chevrons breaking on the shoreline
    for i, sy in enumerate(range(y0 + 14, y1 - 8, 13)):
        sx = x1 - 66 + (i % 3) * 7
        d.arc([sx, sy, sx + 12, sy + 7], start=200, end=340, fill=(255, 255, 255), width=2)
    # track arrow: dashed curve from the eye toward the coast + head
    steps = 12
    ex, ey = x1 - 62, y0 + int(h * 0.34)
    for i in range(steps):
        t0, t1 = i / steps, (i + 0.55) / steps
        xa = cx + 16 + (ex - cx - 16) * t0
        ya = cy + (ey - cy) * t0 - 10 * math.sin(t0 * math.pi)
        xb = cx + 16 + (ex - cx - 16) * t1
        yb = cy + (ey - cy) * t1 - 10 * math.sin(t1 * math.pi)
        d.line([(xa, ya), (xb, yb)], fill=(255, 210, 90), width=2)
    d.polygon([(ex, ey), (ex - 11, ey - 4), (ex - 8, ey + 6)], fill=(255, 210, 90))
    # v6 (Keva rule 3): the old "TO INDIA COAST" label straddled the
    # coastline edge (half on sea, half on sand) — removed; the dashed
    # track arrow alone carries the direction, no half-cut text.
    # rain lines
    for rx in range(x0 + 10, x1 - 50, 16):
        d.line([(rx, y0 + 8), (rx - 5, y0 + 26)], fill=(180, 210, 235), width=2)
    # warning triangle (v6: lowered from y0+10 — its top was clipped by
    # the panel strip; now whole below it, with margin)
    tx, ty = x1 - 34, y0 + 21
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
    # drones (x as fractions of width, so narrow cards stay in-box)
    for (fx, dy) in [(0.12, 18), (0.33, 30), (0.52, 14), (0.74, 26), (0.88, 18)]:
        dx = x0 + int(w * fx)
        d.ellipse([dx - 3, y0 + dy - 2, dx + 8, y0 + dy + 2], fill=(190, 190, 190))
        d.line([(dx + 2, y0 + dy - 6), (dx + 2, y0 + dy + 6)], fill=(190, 190, 190), width=2)
    # interception bursts
    for (bx, by) in [(x0 + int(w * 0.22), y0 + 44), (x0 + int(w * 0.62), y0 + 48),
                     (x0 + int(w * 0.84), y0 + 40)]:
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
    # v6 (Keva rule 3): label moved from y0+4 (fully hidden under the
    # panel strip) to y0+21 — now fully visible inside the scene.
    d.text((x0 + 8, y0 + 21), "1 LIGHT-DAY", font=font(SANS_B, 12), fill=(255, 220, 110))


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
    for fx in [0.14, 0.27, 0.68, 0.82]:
        cx = x0 + int(w * fx)
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
    """Launch day in the city: night skyline with a neon VI sign, a game
    shop billboard reading ON SALE TODAY, and a car on the street below
    (v5 rewrite: a scene that tells the release-day story, no controller
    pictogram). Kept in the scene table though GTA VI is a brief in v5."""
    w, h = x1 - x0, y1 - y0
    # night sky gradient bands
    for i in range(int(h * 0.72)):
        t = i / max(1, int(h * 0.72) - 1)
        d.line([(x0, y0 + i), (x1, y0 + i)],
               fill=(int(26 - 10 * t), int(10 + 6 * t), int(46 + 10 * t)))
    import random as _r
    rnd = _r.Random(71)
    for _ in range(14):
        sx = rnd.randint(x0 + 4, x1 - 4)
        sy = rnd.randint(y0 + 3, y0 + int(h * 0.35))
        d.ellipse([sx, sy, sx + 2, sy + 2], fill=(230, 200, 240))
    # skyline (mid layer) with lit windows
    base = y0 + int(h * 0.72)
    x = x0 + 3
    while x < x1 - 14:
        bw = rnd.randint(13, 24)
        bh = rnd.randint(int(h * 0.22), int(h * 0.44))
        d.rectangle([x, base - bh, x + bw, base], fill=(18, 10, 34))
        for wy in range(base - bh + 3, base - 4, 6):
            for wx in range(x + 2, x + bw - 2, 5):
                if rnd.random() < 0.5:
                    d.rectangle([wx, wy, wx + 2, wy + 3], fill=(255, 214, 90))
        x += bw + 3
    # neon VI sign on the tallest block, left
    d.rounded_rectangle([x0 + 10, y0 + 5, x0 + 40, y0 + 23], radius=4,
                        fill=(40, 10, 60), outline=(255, 80, 190), width=2)
    tf = font(SANS_B, 14)
    d.text((x0 + 25 - tf.getlength("VI") / 2, y0 + 7), "VI", font=tf,
           fill=(255, 120, 210))
    # game-shop billboard, right: the words carry the news
    bw2 = int(w * 0.52)
    bx = x1 - 6 - bw2
    d.rectangle([bx, y0 + 6, bx + bw2, y0 + 24], fill=(250, 214, 90),
                outline=(150, 110, 20), width=1)
    t = "ON SALE TODAY"
    tf2 = font(SANS_B, 11)
    d.text((bx + (bw2 - tf2.getlength(t)) / 2, y0 + 10), t, font=tf2,
           fill=(60, 45, 10))
    d.rectangle([bx + 6, y0 + 24, bx + 9, base], fill=(30, 20, 40))
    d.rectangle([bx + bw2 - 9, y0 + 24, bx + bw2 - 6, base], fill=(30, 20, 40))
    # street (foreground) with a car: body, cabin, wheels, headlight beam
    d.rectangle([x0, base, x1, y1], fill=(14, 8, 24))
    d.line([(x0, base + 2), (x1, base + 2)], fill=(120, 100, 160), width=1)
    car_y = y1 - 8
    cx0 = x0 + int(w * 0.30)
    d.polygon([(cx0, car_y - 6), (cx0 + 8, car_y - 6), (cx0 + 13, car_y - 13),
               (cx0 + 34, car_y - 13), (cx0 + 40, car_y - 6), (cx0 + 52, car_y - 6),
               (cx0 + 52, car_y - 2), (cx0, car_y - 2)], fill=(200, 60, 90))
    d.rectangle([cx0 + 15, car_y - 12, cx0 + 24, car_y - 7], fill=(140, 220, 255))
    d.rectangle([cx0 + 26, car_y - 12, cx0 + 33, car_y - 7], fill=(140, 220, 255))
    for wx in (cx0 + 10, cx0 + 42):
        d.ellipse([wx - 4, car_y - 6, wx + 4, car_y + 2], fill=(20, 20, 26),
                  outline=(200, 200, 210), width=1)
    d.polygon([(cx0 + 52, car_y - 5), (cx0 + 66, car_y - 8), (cx0 + 66, car_y - 1)],
              fill=(255, 240, 170))


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
    # v6 (Keva rule 2): the two upper particles' spikes were clipped by
    # the 17 px panel strip — lowered so every particle is whole with
    # margin; the lowest one nudged up for a bottom margin too.
    parts = [(30, 0.55, 10, (220, 70, 130)), (78, 0.44, 7, (240, 140, 60)),
             (128, 0.58, 12, (220, 70, 130)), (172, 0.46, 6, (60, 200, 180)),
             (56, 0.80, 5, (60, 200, 180))]
    for (ox, fy, r, col) in parts:
        # x offsets were tuned for a 196 px card; scale to the actual box
        cx = x0 + min(int(ox * w / 196.0), w - r - 6)
        cy = y0 + int(h * fy)
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
    """Xavier turning toward the Cook Islands: open-sea spiral, a dashed
    track arrow curving in to a labelled island with a palm (v5 rewrite:
    a track map that tells the story, not a lone swirl)."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(24, 110, 150))
    # lighter sea bands near the top
    for i in range(int(h * 0.4)):
        t = i / max(1, int(h * 0.4) - 1)
        d.line([(x0, y0 + i), (x1, y0 + i)],
               fill=(int(70 - 40 * t), int(150 - 36 * t), int(190 - 36 * t)))
    # cyclone spiral, upper left over the sea
    cx, cy = x0 + int(w * 0.24), y0 + int(h * 0.36)
    for r in range(5, 21, 5):
        d.arc([cx - r, cy - r // 2, cx + r, cy + r // 2], start=30 + r,
              end=310 + r, fill=WHITE, width=2)
    d.ellipse([cx - 3, cy - 2, cx + 3, cy + 2], fill=WHITE)
    t = "XAVIER \u00b7 CAT 5"
    tf = font(SANS_B, 9)
    d.text((cx - tf.getlength(t) / 2, cy + int(h * 0.30)), t, font=tf, fill=WHITE)
    # island landmass, bottom right: sand shore + green top + palm
    ix = x0 + int(w * 0.55)
    iy = y1 - int(h * 0.30)
    d.polygon([(ix, y1), (ix + 14, iy), (ix + 54, iy), (ix + 72, y1)],
              fill=(220, 200, 140))
    d.polygon([(ix + 14, iy), (ix + 54, iy), (ix + 46, iy - 5), (ix + 22, iy - 5)],
              fill=(60, 160, 90))
    tx, ty = ix + 36, iy - 4
    d.line([(tx, ty), (tx + 3, ty - 8), (tx + 7, ty - 14)], fill=(110, 80, 40), width=3)
    for (fx, fy) in [(-11, -18), (-5, -21), (3, -22), (10, -19), (13, -14)]:
        d.line([(tx + 7, ty - 14), (tx + 7 + fx, ty - 14 + (fy + 14))],
               fill=(40, 130, 70), width=2)
    t2 = "RAROTONGA"
    d.text((ix + 36 - tf.getlength(t2) / 2, y1 - 11), t2, font=tf,
           fill=(90, 60, 20))
    # dashed track arrow: from the eye, curving down toward the island
    steps = 12
    ex, ey = ix + 2, iy - 8
    for i in range(steps):
        t0, t1 = i / steps, (i + 0.55) / steps
        xa = cx + 14 + (ex - cx - 14) * t0
        ya = cy + 8 + (ey - cy - 8) * t0 + 12 * math.sin(t0 * math.pi)
        xb = cx + 14 + (ex - cx - 14) * t1
        yb = cy + 8 + (ey - cy - 8) * t1 + 12 * math.sin(t1 * math.pi)
        d.line([(xa, ya), (xb, yb)], fill=(255, 210, 90), width=2)
    d.polygon([(ex, ey), (ex - 11, ey - 5), (ex - 7, ey + 6)], fill=(255, 210, 90))
    # rain streaks, right side
    for rx in range(x1 - 46, x1 - 8, 11):
        d.line([(rx, y0 + 6), (rx - 4, y0 + 20)], fill=(190, 220, 240), width=2)


def scene_cop31(d, x0, y0, x1, y1):
    """COP31 in Antalya: a conference centre with a COP31 banner across
    its glass front, a flag row on the roof and delegates on the plaza
    (v5 rewrite: the venue and its banner tell the story, not a lone
    flag pictogram). Kept in the table though COP31 is a brief in v5."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(198, 224, 236))
    d.ellipse([x1 - 26, y0 + 3, x1 - 11, y0 + 18], fill=(255, 190, 60))
    # conference building: main block + glass band
    bx0, bx1 = x0 + 10, x1 - 10
    by0, by1 = y0 + int(h * 0.30), y1 - 10
    d.rectangle([bx0, by0, bx1, by1], fill=(238, 240, 242))
    d.rectangle([bx0, by0 + 14, bx1, by1 - 6], fill=(120, 170, 205))
    for gx in range(bx0 + 8, bx1 - 6, 12):
        d.line([(gx, by0 + 14), (gx, by1 - 6)], fill=(90, 140, 180), width=1)
    # the banner across the top of the building, carrying the name
    d.rectangle([bx0, by0, bx1, by0 + 14], fill=(24, 90, 60))
    t = "COP31 \u00b7 ANTALYA"
    tf = font(SANS_B, 11)
    d.text((x0 + w / 2 - tf.getlength(t) / 2, by0 + 2), t, font=tf, fill=WHITE)
    # flag row on poles along the roof
    flag_cols = [(206, 32, 32), (36, 64, 140), (250, 210, 40), (34, 139, 92),
                 (255, 255, 255)]
    fx = x0 + int(w * 0.16)
    step = max(14, int(w * 0.16))
    for col in flag_cols:
        if fx + step - 4 > x1 - 12:
            break
        d.rectangle([fx, by0 - 12, fx + 2, by0], fill=(60, 60, 60))
        d.rectangle([fx + 2, by0 - 12, fx + step - 4, by0 - 4], fill=col)
        fx += step
    # plaza + delegate figures (foreground)
    d.rectangle([x0, y1 - 10, x1, y1], fill=(150, 170, 150))
    for i, fx2 in enumerate([0.22, 0.38, 0.55, 0.71]):
        cx = x0 + int(w * fx2)
        suit = (40, 40, 60) if i % 2 == 0 else (90, 50, 50)
        d.ellipse([cx - 3, y1 - 17, cx + 3, y1 - 11], fill=(232, 190, 150))
        d.polygon([(cx - 4, y1 - 1), (cx + 4, y1 - 1), (cx + 3, y1 - 11),
                   (cx - 3, y1 - 11)], fill=suit)


def scene_euloan(d, x0, y0, x1, y1):
    """EU loan for Ukraine: EU circle of stars, gold bars, Ukraine band."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(24, 52, 120))
    # circle of 12 gold stars, left
    cx, cy, rr = x0 + int(w * 0.24), y0 + h // 2, max(10, h // 4)
    for k in range(12):
        a = math.radians(k * 30 - 90)
        sx, sy = cx + rr * math.cos(a), cy + rr * math.sin(a)
        _flag_star(d, sx, sy, 3, (255, 204, 0))
    d.text((cx - 4, cy - 8), "\u20ac", font=font(SERIF_B, 17), fill=(255, 204, 0))
    # gold bars, centre-right
    bx = x0 + int(w * 0.52)
    for row in range(3):
        n = 3 - row
        for i in range(n):
            gx = bx + i * 20 + row * 10
            gy = y1 - 12 - row * 9
            d.polygon([(gx, gy), (gx + 5, gy - 5), (gx + 21, gy - 5),
                       (gx + 16, gy)], fill=(240, 196, 60))
            d.polygon([(gx, gy), (gx + 5, gy - 5), (gx + 21, gy - 5),
                       (gx + 16, gy)], outline=(160, 120, 20))
    # Ukraine band (blue over yellow) along the top right
    d.rectangle([x0 + int(w * 0.55), y0 + 5, x1 - 8, y0 + 11], fill=(64, 140, 220))
    d.rectangle([x0 + int(w * 0.55), y0 + 11, x1 - 8, y0 + 17], fill=(250, 210, 40))
    t = "\u20ac45bn"
    tf = font(SERIF_B, 15)
    d.text((x1 - 10 - tf.getlength(t), y0 + 22), t, font=tf, fill=(255, 255, 255))


def scene_fed(d, x0, y0, x1, y1):
    """The Fed: neoclassical facade, columns, a rising rate arrow."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(216, 208, 188))
    base = y1 - 8
    # pediment + entablature
    d.polygon([(x0 + 12, y0 + 22), (x0 + w // 2, y0 + 6), (x1 - 12, y0 + 22)],
              fill=(240, 236, 224))
    d.rectangle([x0 + 12, y0 + 22, x1 - 12, y0 + 28], fill=(240, 236, 224))
    # columns
    for fx in [0.16, 0.34, 0.52, 0.70, 0.86]:
        cx = x0 + int(w * fx)
        d.rectangle([cx - 4, y0 + 28, cx + 4, base - 6], fill=(244, 240, 230))
        d.rectangle([cx - 6, y0 + 28, cx + 6, y0 + 32], fill=(228, 222, 204))
    # steps
    d.rectangle([x0 + 8, base - 6, x1 - 8, base - 2], fill=(228, 222, 204))
    d.rectangle([x0 + 4, base - 2, x1 - 4, base + 2], fill=(214, 206, 186))
    # rising arrow across the facade
    d.line([(x0 + 14, base - 12), (x1 - 26, y0 + 34)], fill=(178, 34, 34), width=3)
    d.polygon([(x1 - 26, y0 + 34), (x1 - 40, y0 + 36), (x1 - 30, y0 + 46)],
              fill=(178, 34, 34))
    # tag below the panel strip line (the strip overlays the top 18 px)
    t = "+50bp?"
    tf = font(SANS_B, 11)
    d.text((x1 - 8 - tf.getlength(t), y0 + 21), t, font=tf, fill=(178, 34, 34))


def scene_ukinfl(d, x0, y0, x1, y1):
    """UK inflation: price tags climbing a rising trend line, pound sign."""
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=(236, 232, 222))
    # rising trend line
    # v6 (Keva rules 2-3): line head + top tag lowered fully below the
    # 17 px panel strip (they were clipped by it) — whole, with margin.
    d.line([(x0 + 8, y1 - 12), (x1 - 12, y0 + 25)], fill=(178, 34, 34), width=3)
    d.polygon([(x1 - 12, y0 + 25), (x1 - 27, y0 + 26), (x1 - 18, y0 + 37)],
              fill=(178, 34, 34))
    # three price tags climbing the line
    tags = [(0.16, 0.68, "\u00a32.10"), (0.44, 0.48, "\u00a33.40"), (0.70, 0.42, "\u00a34.85")]
    tf = font(SANS_B, 10)
    for (fx, fy, t) in tags:
        tx, ty = x0 + int(w * fx), y0 + int(h * fy)
        tw = tf.getlength(t) + 12
        d.polygon([(tx, ty), (tx + 8, ty - 7), (tx + tw, ty - 7),
                   (tx + tw, ty + 9), (tx, ty + 9)], fill=(250, 214, 90),
                  outline=(150, 110, 20))
        d.ellipse([tx + 3, ty - 1, tx + 7, ty + 3], fill=(236, 232, 222))
        d.text((tx + 10, ty - 3), t, font=tf, fill=(60, 45, 10))
    # (no big "3.6%" in-scene: the panel strip overlays the top-left, and
    # the panel title already carries the figure)


SCENES = {
    "apec": scene_apec, "gulf": scene_gulf, "manila": scene_manila,
    "markets": scene_markets, "akvan": scene_akvan, "ukraine": scene_ukraine,
    "voyager": scene_voyager, "caracas": scene_caracas,
    "gta": scene_gta, "alaska": scene_alaska, "ebola": scene_ebola,
    "tennis": scene_tennis, "xavier": scene_xavier, "cop31": scene_cop31,
    "euloan": scene_euloan, "fed": scene_fed, "ukinfl": scene_ukinfl,
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
    f_date = font(SERIF_B, 38)
    d.text((MARGIN, y), "THE WORLD IN ONE PAGE", font=f_small, fill=INK)
    right = "%d STORIES  \u00b7  ALL DATED 18 NOV" % STORY_TOTAL
    d.text((W - MARGIN - f_small.getlength(right), y), right, font=f_small, fill=RED)
    date = "WEDNESDAY 18 NOVEMBER 2026"
    d.text((MARGIN, y + 13), date, font=f_date, fill=INK)
    d.line([(MARGIN, y + 54), (W - MARGIN, y + 54)], fill=RULE, width=3)
    return y + 56


def region_tally():
    counts = {r: 0 for r in REGION_ORDER}
    for p in PANELS:
        counts[p["region"]] += 1
    for (_, _, _, _, region) in BRIEFS:
        counts[region] += 1
    return counts


def draw_region_strip(d, y, counts):
    total = sum(counts.values())
    assert total == STORY_TOTAL, "story total mismatch: %d" % total
    f = font(SANS_B, 12)
    x = MARGIN
    seg_w = CONTENT_W / len(REGION_ORDER)
    for region in REGION_ORDER:
        col = REGION_COLORS[region]
        d.rectangle([x, y, x + seg_w - 2, y + 16], fill=col)
        label = "%s %d" % (region, counts[region])
        tw = f.getlength(label)
        d.text((x + (seg_w - 2 - tw) / 2, y + 2), label, font=f, fill=WHITE)
        x += seg_w
    return y + 20


def draw_key_numbers(d, y):
    f_big = font(SERIF_B, 21)
    f_cap = font(SANS, 9)
    d.text((MARGIN, y + 2), "THE DAY\nIN NUMBERS", font=font(SANS_B, 10), fill=INK_SOFT)
    x = MARGIN + 92
    col_w = (CONTENT_W - 92) / len(KEY_NUMBERS)
    for big, cap in KEY_NUMBERS:
        d.text((x + 4, y), big, font=f_big, fill=NAVY)
        lines = wrap(cap, f_cap, col_w - 10)
        draw_wrapped(d, lines, x + 4, y + 23, f_cap, INK_SOFT, 10)
        x += col_w
        if x < W - MARGIN:
            d.line([(x - 4, y + 2), (x - 4, y + 30)], fill=(200, 200, 200), width=1)
    return y + 43


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
    d.line([(MARGIN, y + 13), (W - MARGIN, y + 13)], fill=RULE, width=2)
    return y + 17


def draw_panel(d, p, x0, y0, x1, y1, title_fnt, sum_fnt, label_fnt, strip_fnt,
               title_col, report, ill_h, label_bottom=False):
    """One illustrated panel. Returns nothing; appends wrap report."""
    d.rectangle([x0, y0, x1, y1], fill=PANEL_BG, outline=PANEL_BORDER, width=1)
    # illustration
    SCENES[p["scene"]](d, x0 + 1, y0 + 1, x1 - 1, y0 + 1 + ill_h)
    # v5 strip: a cream bar across the top of the illustration (rank-1
    # pattern) — a small region-colour chip carries the story number,
    # then CITY - TOPIC in navy. No more full-colour confetti bars.
    d.rectangle([x0 + 1, y0 + 1, x1 - 1, y0 + 1 + 17], fill=STRIP_CREAM)
    d.line([(x0 + 1, y0 + 18), (x1 - 1, y0 + 18)], fill=PANEL_BORDER, width=1)
    num = str(p["n"])
    nw = strip_fnt.getlength(num)
    d.rectangle([x0 + 4, y0 + 3, x0 + 4 + nw + 6, y0 + 15],
                fill=REGION_COLORS[p["region"]])
    d.text((x0 + 7, y0 + 3), num, font=strip_fnt, fill=WHITE)
    strip = "%s \u00b7 %s" % (p["city"], p["topic"])
    d.text((x0 + 4 + nw + 12, y0 + 3), strip, font=strip_fnt, fill=NAVY)
    # attribution: a DARK chip with white text (v4's pale grey label was
    # nearly unreadable). Heroes: a dark segment at the right end of the
    # strip. Cards: a dark chip at the bottom right, below the summary.
    lab = p["label"]
    lw = label_fnt.getlength(lab)
    if label_bottom:
        ly = y1 - 14
        d.rectangle([x1 - 1 - lw - 8, ly, x1 - 1, ly + 13], fill=INK)
        d.text((x1 - 1 - lw - 4, ly + 2), lab, font=label_fnt, fill=WHITE)
    else:
        d.rectangle([x1 - 1 - lw - 8, y0 + 1, x1 - 1, y0 + 1 + 15], fill=INK)
        d.text((x1 - 1 - lw - 4, y0 + 3), lab, font=label_fnt, fill=WHITE)
    # title (uniform black ink, max 2 lines)
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
    """Map left + MORE NEWS right. v5: the map block is taller, its
    landmass dots darker (+40% contrast) and its pins bigger; briefs are
    set in the page serif (one line each, verified against the font
    metrics), numbers in a single dark red, city lead-ins bold, flowing
    down two columns."""
    map_w = 300
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
    # dot-matrix continents (darker than v4: the pale map washed out)
    step = 5
    for gy in range(map_y0 + 3, map_y1 - 2, step):
        for gx in range(map_x0 + 3, map_x1 - 2, step):
            lon = (gx - map_x0) / (map_x1 - map_x0) * 360.0 - 180.0
            lat = 90.0 - (gy - map_y0) / (map_y1 - map_y0) * 150.0
            for poly in CONTINENTS:
                if point_in_poly(lon, lat, poly):
                    d.ellipse([gx - 1, gy - 1, gx + 1, gy + 1], fill=(74, 92, 82))
                    break
    # pins for the illustrated panels (v5: radius 12, was 9)
    pin_f = font(SANS_B, 11)
    for p in PANELS:
        px, py = lonlat_to_xy(p["lon"], p["lat"], map_x0, map_y0, map_x1, map_y1)
        col = REGION_COLORS[p["region"]]
        d.ellipse([px - 12, py - 12, px + 12, py + 12], fill=col, outline=WHITE, width=2)
        num = str(p["n"])
        d.text((px - pin_f.getlength(num) / 2, py - 8), num, font=pin_f, fill=WHITE)
    report["pins"] = len(PANELS)
    # Voyager callout (probe is 25.9bn km out - off the map, not a place pin)
    voy_n = next(p["n"] for p in PANELS if p["scene"] == "voyager")
    d.text((map_x0 + 4, map_y1 + 4),
           "%d Voyager 1: 25.9bn km out - off this map," % voy_n,
           font=font(SANS_I, 10), fill=INK_SOFT)
    d.text((map_x0 + 4, map_y1 + 18), "one light-day from Earth (NASA/JPL).",
           font=font(SANS_I, 10), fill=INK_SOFT)
    # legend
    ly = map_y1 + 38
    d.text((MARGIN + 8, ly), "PIN No. = STORY No.  Pins mark the %d" % len(PANELS),
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
    right = "%d MORE STORIES" % len(BRIEFS)
    d.text((more_x1 - 8 - f_head.getlength(right), y + 6), right, font=f_head, fill=RED)
    d.line([(more_x0, y + 22), (more_x1, y + 22)], fill=RULE, width=1)
    brief_f = font(SERIF, 12)
    brief_bf = font(SERIF_B, 12)
    num_f = font(SERIF_B, 12)
    col_w = (more_x1 - more_x0 - 16) / 2
    half = (len(BRIEFS) + 1) // 2
    cols = [BRIEFS[:half], BRIEFS[half:]]
    report["brief_lines"] = {}
    lead = 12.6
    for ci, col_briefs in enumerate(cols):
        bx = more_x0 + 8 + ci * col_w
        by = y + 27
        for (n, city, head, src, region) in col_briefs:
            d.text((bx, by), str(n), font=num_f, fill=BRIEF_RED)
            text = "%s \u2014 %s. %s" % (city, head, src)
            lines = wrap(text, brief_f, col_w - 30)
            report["brief_lines"][n] = len(lines)
            # bold city lead-in opens the first line (rank-1 pattern)
            lead_txt = "%s \u2014 " % city
            lw = brief_bf.getlength(lead_txt)
            rest = lines[0][len(lead_txt):] if lines[0].startswith(lead_txt) else lines[0]
            d.text((bx + 26, by), lead_txt, font=brief_bf, fill=INK)
            d.text((bx + 26 + lw, by), rest, font=brief_f, fill=INK)
            for li, line in enumerate(lines[1:], start=1):
                d.text((bx + 26, by + li * lead), line, font=brief_f, fill=INK)
            by += len(lines) * lead + 0.2
        assert by <= y + band_h - 2, \
            "brief column %d overflows band by %.1f px" % (ci, by - (y + band_h - 2))
    return y + band_h


# DATE CHECK items, one per line with its own date (v5: itemised like
# dev #10's, not v4's run-on paragraphs — criterion 1 is checked first,
# so the exclusions must be individually visible).
DATE_BEFORE = [
    ("15 Nov", "Gaza aid statement"),
    ("16 Nov", "CCW Geneva \u2014 no decision"),
    ("16 Nov", "US chip-export rule"),
    ("17 Nov", "SAFF final & Dhoni retirement"),
    ("17 Nov", "Knesset speaker vote"),
    ("16\u201317 Nov", "Kerch bridge collapse"),
    ("17 Nov", "Nvidia results"),
    ("17 Nov", "Alaska Senate call"),
]
DATE_FUTURE = [
    ("Thu 19 Nov", "Trump\u2013Xi\u2013Putin trilateral"),
    ("Thu 19 Nov", "Anthropic trades as ANT"),
    ("Fri 20 Nov", "Cyclone Akvan landfall"),
    ("Fri 20 Nov", "COP31 close"),
]


def date_check_height():
    """Title row + group row + 4 item rows at pitch 12 + padding."""
    return 17 + 11 + 4 * 12 + 4


def draw_date_check(d, y, h):
    d.rectangle([MARGIN, y, W - MARGIN, y + h], fill=BLACK)
    f_head = font(SANS_B, 13)
    f_intro = font(SANS, 10)
    f_grp = font(SANS_B, 10)
    f_date = font(SANS_B, 10)
    f_item = font(SANS, 10)
    d.text((MARGIN + 10, y + 4), "DATE CHECK", font=f_head, fill=(255, 210, 90))
    intro = ("Every story above was first reported Wednesday 18 November 2026, "
             "as far as we could check.")
    d.text((MARGIN + 118, y + 6), intro, font=f_intro, fill=WHITE)
    col_w = (CONTENT_W - 20) / 3
    xs = [MARGIN + 10, MARGIN + 10 + col_w, MARGIN + 10 + 2 * col_w]
    d.text((xs[0], y + 19), "NOT NEWS \u2014 FIRST REPORTED BEFORE 18 NOV:",
           font=f_grp, fill=(255, 210, 90))
    d.text((xs[2], y + 19), "NOT YET HAPPENED:", font=f_grp, fill=(255, 210, 90))
    rows = max((len(DATE_BEFORE) + 1) // 2, len(DATE_FUTURE))
    for r in range(rows):
        iy = y + 30 + r * 12
        for ci, item in ((0, DATE_BEFORE[r] if r < len(DATE_BEFORE) else None),
                         (1, DATE_BEFORE[r + 4] if r + 4 < len(DATE_BEFORE) else None),
                         (2, DATE_FUTURE[r] if r < len(DATE_FUTURE) else None)):
            if item is None:
                continue
            dt, what = item
            d.text((xs[ci], iy), dt, font=f_date, fill=(255, 210, 90))
            d.text((xs[ci] + f_date.getlength(dt) + 4, iy), "\u2014 " + what,
                   font=f_item, fill=(228, 228, 228))
    return y + h


def draw_footer(d, y):
    f = font(SANS, 9)
    text = ("Sources: Reuters \u00b7 AP \u00b7 BBC \u00b7 Bloomberg \u00b7 CNBC \u00b7 ONS \u00b7 IMD \u00b7 "
            "NASA/JPL \u00b7 UN News \u00b7 WHO \u00b7 Amnesty \u00b7 IAEA \u00b7 ICC \u00b7 FIFA \u00b7 "
            "Federal Reserve. All %d stories happened, or were first reported, on Wednesday "
            "18 November 2026; claims are attributed. Original flat illustrations."
            ) % STORY_TOTAL
    lines = wrap(text, f, CONTENT_W)
    draw_wrapped(d, lines, MARGIN, y, f, INK_SOFT, 11)
    return y + len(lines) * 11


# ---------------------------------------------------------------- build
def check_fit(panels, widths, title_fnt, sum_fnt, ill_h, row_h, reserve=2):
    """Fail loudly if any panel's text would spill out of its box.
    reserve: pixels to keep clear at the panel bottom (15 for card rows,
    whose attribution chip sits at the bottom right)."""
    for p, pw in zip(panels, widths):
        tl = wrap(p["title"], title_fnt, pw - 12)
        sl = wrap(p["summary"], sum_fnt, pw - 12)
        assert len(tl) <= 2, "panel %d title wraps to %d lines" % (p["n"], len(tl))
        assert len(sl) >= 2, "panel %d summary under 2 lines" % p["n"]
        need = ill_h + 6 + len(tl) * (title_fnt.size + 3) + 2 \
            + len(sl) * (sum_fnt.size + 3)
        assert need <= row_h - reserve, \
            "panel %d needs %d px, row is %d (reserve %d)" % (p["n"], need, row_h, reserve)


def build():
    # v5: 13 big informative panels, one serif family, cream strips,
    # dark attribution chips, itemised DATE CHECK. No hue solving.
    report = {"design": "v6: v5 + Keva composition fixes (whole subjects with margin, no half-cut in-scene text)",
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

    # Heroes (panels 1-3), illustration strip 106 px (v4: 78; the audit
    # target was 105-110 so the hero scenes can actually tell the story)
    hero_y0 = y
    hero_h = 186
    hero_w = (CONTENT_W - 2 * 6) // 3
    hero_tf, hero_sf = font(SERIF_B, 17), font(SERIF, 12)
    check_fit(PANELS[:3], [hero_w] * 3, hero_tf, hero_sf, 106, hero_h)
    for i, p in enumerate(PANELS[:3]):
        x0 = MARGIN + i * (hero_w + 6)
        draw_panel(d, p, x0, hero_y0, x0 + hero_w, hero_y0 + hero_h,
                   hero_tf, hero_sf, font(SANS_B, 8),
                   font(SANS_B, 10), INK, report, ill_h=106)
    y = hero_y0 + hero_h + 3

    # Card rows: A = panels 4-8, B = panels 9-13 (5 across each).
    # Illustration strips 72 px (v4: 62).
    card_tf, card_sf = font(SERIF_B, 12), font(SERIF, 11)
    rows = [PANELS[3:8], PANELS[8:13]]
    for row in rows:
        row_h = 153
        n = len(row)
        card_w = (CONTENT_W - (n - 1) * 6) // n
        check_fit(row, [card_w] * n, card_tf, card_sf, 72, row_h, reserve=15)
        card_y0 = y
        for j, p in enumerate(row):
            x0 = MARGIN + j * (card_w + 6)
            draw_panel(d, p, x0, card_y0, x0 + card_w, card_y0 + row_h,
                       card_tf, card_sf, font(SANS_B, 7),
                       font(SANS_B, 8), INK, report, ill_h=72,
                       label_bottom=True)
        y = card_y0 + row_h + 3

    # Bottom band: map + MORE NEWS (absorbs remaining space before DATE CHECK)
    date_h = date_check_height()
    foot_h = 22
    band_h = (H - MARGIN) - date_h - 3 - foot_h - 2 - y
    y = draw_bottom_band(d, y, band_h, None, report)
    y += 3
    y = draw_date_check(d, y, date_h)
    y += 2
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
    print("WROTE %s sha256=%s bytes=%d stories=%d" %
          (OUT, sha, report["size_bytes"], report["story_total"]))
    print(json.dumps(report, sort_keys=True))
    return report


if __name__ == "__main__":
    build()
