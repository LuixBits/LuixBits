#!/usr/bin/env python3
"""Forest profile generator for LuixBits/LuixBits — fully custom, jdx-style.

Every README section is a pre-rendered, fixed-size (880px) SVG with Hurmit
Mono embedded as a subset data URI. A GitHub Action regenerates daily from
real data (data.json: stars, language bytes, contribution calendar).

Sections, each in a night and a garden-day variant:
  header            MOTD with layered pines, mist, fireflies and the REAL
                    moon phase, computed from today's date
  link buttons      one SVG per link so each is its own <a> in the README
  trail map         featured projects as waypoints on one continuous map,
                    sliced into stacked row SVGs so each waypoint row is
                    individually clickable (jdx's console-slicing trick)
  contribution      one pine per day, log-scaled height from real commits
  language rings    real language bytes across all public repos, with a
                    tree-stump cross-section
  campfire          footer; animated flame at night, smoke by day

Usage:
  python3 generate.py [--out DIR]   render SVGs (default: script dir)
  python3 generate.py --fetch       refresh data.json from the GitHub API
                                    (uses GH_TOKEN / GITHUB_TOKEN if set;
                                    calendar needs a token, rest works bare)
"""
import base64
import datetime
import json
import math
import os
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).parent
LOGIN = "LuixBits"
FEATURED = ["luix_nix_config", "luixbits-roomplanner.nvim", "TextSight", "luixbits-noctalia-plugins"]

MONO = "'HurmitSub','Hurmit Nerd Font Mono','Hurmit','Hermit',monospace"

# garden corner of lupe-webfolio
GOLD = "#D9A441"
LEAF = "#6BBF7B"
STEM = "#3F6D4E"
HUB = "#2F4F3A"
FIREFLY = "#FFD36E"
FF_CORE = "#FFE9B3"
# stump wood
BARK, WOOD, RING, CRACK = "#3E2F23", "#B08D5F", "#8A6B4A", "#6E5137"

LANG_COLORS = {"Lua": "#8A93CF", "Svelte": "#D08057", "TypeScript": "#5F86AD",
               "Nix": "#86AEDC", "Vue": "#58A882"}
OTHER_COLOR = "#8A9B8F"


def font_css():
    r = base64.b64encode((HERE / "fonts/hurmit-regular.woff").read_bytes()).decode()
    b = base64.b64encode((HERE / "fonts/hurmit-bold.woff").read_bytes()).decode()
    return (
        "@font-face{font-family:'HurmitSub';font-weight:400;"
        f"src:url(data:font/woff;base64,{r}) format('woff')}}"
        "@font-face{font-family:'HurmitSub';font-weight:700;"
        f"src:url(data:font/woff;base64,{b}) format('woff')}}"
    )


COMMON_CSS = (
    font_css()
    + "text{font-family:" + MONO + "}"
    ".tw{animation:tw var(--d,5s) ease-in-out var(--dd,0s) infinite alternate}"
    ".drift{animation:dr var(--d,40s) ease-in-out infinite alternate}"
    ".ffw{animation:ffd var(--d,8s) ease-in-out var(--dd,0s) infinite alternate}"
    ".ffp{animation:ffp var(--p,4s) ease-in-out var(--dd,0s) infinite alternate}"
    ".mote{animation:mt var(--p,6s) ease-in-out var(--dd,0s) infinite alternate}"
    ".blink{animation:bl 1.3s steps(2,start) infinite}"
    ".fl{transform-box:fill-box;transform-origin:50% 100%;"
    "animation:flm var(--fd,1s) ease-in-out infinite alternate}"
    ".spk{animation:spk var(--d,2.6s) linear var(--dd,0s) infinite}"
    ".smoke{animation:smk 5s ease-in-out infinite alternate}"
    ".br{animation:br var(--p,7s) ease-in-out var(--dd,0s) infinite alternate}"
    "@keyframes tw{from{opacity:.12}to{opacity:.75}}"
    "@keyframes dr{to{transform:translateX(var(--tx,20px))}}"
    "@keyframes ffd{to{transform:translate(var(--tx,10px),var(--ty,-8px))}}"
    "@keyframes ffp{from{opacity:.12}to{opacity:1}}"
    "@keyframes mt{from{opacity:.05}to{opacity:.4}}"
    "@keyframes bl{to{visibility:hidden}}"
    "@keyframes flm{from{transform:scaleY(.93)}to{transform:scaleY(1.07)}}"
    "@keyframes spk{0%{transform:translateY(0);opacity:.85}100%{transform:translateY(-30px);opacity:0}}"
    "@keyframes smk{from{opacity:.22}to{opacity:.55}}"
    "@keyframes br{from{opacity:.45}to{opacity:1}}"
    ".sway{animation:sway var(--p,14s) ease-in-out infinite alternate}"
    ".hike{animation:hike 85s linear infinite}"
    ".bob{animation:bob .7s ease-in-out infinite alternate}"
    ".shoot{animation:shoot 13s linear 4s infinite;opacity:0}"
    ".cloud{animation:cloud var(--p,150s) linear var(--dd,0s) infinite}"
    ".flut{transform-box:fill-box;transform-origin:center;animation:flut .22s ease-in-out infinite alternate}"
    ".grow{transform-box:fill-box;transform-origin:left center;animation:grow .9s ease-out var(--dd,0s) both}"
    ".puff{animation:puff var(--p,6s) ease-out var(--dd,0s) infinite;opacity:0}"
    ".owl{animation:owl 7s linear var(--dd,0s) infinite}"
    ".draw{animation:draw 2.2s ease-out var(--dd,.2s) both}"
    ".fall{animation:fall var(--d,12s) linear var(--dd,0s) infinite}"
    ".fade{animation:fade 1.2s ease-out var(--dd,1s) both;opacity:0}"
    "@keyframes sway{from{transform:skewX(.5deg)}to{transform:skewX(-.5deg)}}"
    "@keyframes hike{from{transform:translate(930px,281px)}to{transform:translate(-70px,281px)}}"
    "@keyframes bob{from{transform:translateY(0)}to{transform:translateY(-1.6px)}}"
    "@keyframes shoot{0%{transform:translate(690px,28px);opacity:0}2%{opacity:.9}"
    "6%{transform:translate(470px,88px);opacity:0}100%{transform:translate(470px,88px);opacity:0}}"
    "@keyframes cloud{from{transform:translateX(-200px)}to{transform:translateX(1080px)}}"
    "@keyframes flut{from{transform:scaleX(1)}to{transform:scaleX(.35)}}"
    "@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
    "@keyframes puff{0%{transform:translateY(0) scale(.6);opacity:0}15%{opacity:.35}"
    "100%{transform:translateY(-34px) scale(1.4);opacity:0}}"
    "@keyframes owl{0%,91%,96%,100%{opacity:1}93%,94.5%{opacity:0}}"
    "@keyframes draw{from{stroke-dashoffset:var(--len,1000)}to{stroke-dashoffset:0}}"
    "@keyframes fall{from{transform:translate(0,-16px) rotate(0)}"
    "to{transform:translate(var(--fx,40px),352px) rotate(280deg)}}"
    "@keyframes fade{from{opacity:0}to{opacity:1}}"
    "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
)


def svg_open(w, h, title, desc):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">'
        f"<title id=\"t\">{title}</title><desc id=\"d\">{desc}</desc>"
        f"<style>{COMMON_CSS}</style>"
    )


def lerp_hex(c0, c1, t):
    a = [int(c0[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(c1[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))


def pine(x, base, h, w, tiers=3, spire=False):
    if spire or tiers == 1:
        half = w * (0.34 if spire else 0.7)
        return [f"{x:.1f},{base - h:.1f} {x - half:.1f},{base:.1f} {x + half:.1f},{base:.1f}"]
    if tiers == 2:
        spec = [(0.0, 0.52, 0.62), (0.34, 0.95, 0.72)]
    else:
        spec = [(0.0, 0.42, 0.46), (0.26, 0.70, 0.46), (0.52, 1.00, 0.52)]
    polys = []
    for drop, hw, th in spec:
        top = base - h * (1 - drop)
        half = w * hw
        bot = min(base, top + h * th)
        polys.append(f"{x:.1f},{top:.1f} {x - half:.1f},{bot:.1f} {x + half:.1f},{bot:.1f}")
    return polys


def pines_g(x, base, h, w, color, tiers=3):
    return (f'<g fill="{color}">'
            + "".join(f'<polygon points="{p}"/>' for p in pine(x, base, h, w, tiers=tiers)) + "</g>")


def treeline(rng, base, x0, x1, h_rng, w_rng, step_rng, color, opacity, band_to, damp=None, spire_p=0.10):
    polys = []
    x = x0 + rng.uniform(0, step_rng[0])
    while x < x1:
        h = rng.uniform(*h_rng)
        w = rng.uniform(*w_rng)
        if damp and damp[0] < x < damp[1]:
            h *= damp[2]
        spire = rng.random() < spire_p and h > sum(h_rng) / 2
        if spire:
            h *= 1.2
        polys += pine(x, base, h, w, spire=spire)
        x += rng.uniform(*step_rng)
    shapes = "".join(f'<polygon points="{p}"/>' for p in polys)
    band = f'<rect x="{x0}" y="{base - 7:.1f}" width="{x1 - x0}" height="{band_to - base + 7:.1f}"/>'
    op = f' opacity="{opacity}"' if opacity < 1 else ""
    return f'<g fill="{color}"{op}>{shapes}{band}</g>'


def smooth_path(pts):
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def moon_phase(day=None):
    """Approximate illuminated fraction and waxing flag for a date."""
    day = day or datetime.date.today()
    days = (day - datetime.date(2000, 1, 6)).days + 0.76  # new moon 2000-01-06 18:14 UTC
    p = (days % 29.530588) / 29.530588
    return (1 - math.cos(2 * math.pi * p)) / 2, p < 0.5


# ---------------------------------------------------------------- themes
NIGHT = dict(
    sky=[(0, "#030B07"), (0.58, "#0A2015"), (1, "#153826")],
    horizon="#3E7B55", horizon_op=0.28,
    orb="#E9F3E3", orb_glow="#CFE7D0", orb_glow_op=0.38, orb_r=24, glow_r=64,
    star="#DFF0E2",
    layers=[
        (232, (20, 50), (8, 13), (11, 21), "#1E4430", 0.55, (44, 410, 0.45)),
        (254, (32, 70), (10, 16), (14, 27), "#173627", 0.80, (44, 410, 0.45)),
        (282, (46, 93), (13, 19), (19, 35), "#102819", 1.00, (44, 470, 0.50)),
        (322, (67, 126), (16, 24), (29, 56), "#0A1A10", 1.00, (30, 500, 0.42)),
    ],
    mist="#B9D6C1", mist_ops=(0.06, 0.09, 0.12),
    prompt="#7FA98C", name="#EDF6ED", name_glow="#7FD6A0", glow_op=0.18, tagline="#A9C4B1",
)
DAY = dict(
    sky=[(0, "#F5FAF5"), (0.58, "#E9F2E8"), (1, "#D9E7D4")],
    horizon="#F2DD9D", horizon_op=0.50,
    orb="#F0D98F", orb_glow="#ECD27E", orb_glow_op=0.55, orb_r=30, glow_r=92,
    star=None,
    layers=[
        (232, (20, 50), (8, 13), (11, 21), "#B7CFBA", 0.80, (44, 410, 0.45)),
        (254, (32, 70), (10, 16), (14, 27), "#8FB597", 0.92, (44, 410, 0.45)),
        (282, (46, 93), (13, 19), (19, 35), "#567E63", 1.00, (44, 470, 0.50)),
        (322, (67, 126), (16, 24), (29, 56), HUB, 1.00, (30, 500, 0.42)),
    ],
    mist="#FFFFFF", mist_ops=(0.24, 0.30, 0.34),
    prompt="#4F8A63", name="#12251A", name_glow="#86B894", glow_op=0.12, tagline="#3C5346",
)

T_DARK = dict(
    light=False, sfx="",
    panel="#0A1C12", pline="#1E4028", inset="#123124", iline="#28513A",
    ink="#ECF5EC", dim="#9CB9A4", faint="#6F8F7B",
    bbox="#0D2316", bline="#28513A", bink="#D6EAD9", icon=LEAF, gold=GOLD,
    gbox="#0B150F", gline="#2C3E33", gink="#5F7566", gsuf="#8A7347",
    trail="#C9A97A", creek="#3E7876", creek_op=0.5, contour_op=0.05,
    tree1="#143122", tree2="#1C4530",
    ground="#16331F", lerp0="#163320", lerp1="#4F8A63",
    star="#DFF0E2", ff=True,
)
T_LIGHT = dict(
    light=True, sfx="-light",
    panel="#F2F8F1", pline="#D5E3D4", inset="#E4EFE4", iline="#C9DACB",
    ink="#12251A", dim="#3C5346", faint="#5C7466",
    bbox="#EDF5ED", bline="#C9DACB", bink="#1C3A2B", icon=STEM, gold="#C48F2F",
    gbox="#F0F4F0", gline="#DCE3DC", gink="#8B9A8F", gsuf="#B09A6A",
    trail="#7A5F3F", creek="#2B9CBA", creek_op=0.4, contour_op=0.05,
    tree1="#C4D8C4", tree2="#A8C6AD",
    ground="#C9DACB", lerp0="#C4D8C4", lerp1="#3F6D4E",
    star=None, ff=False,
)

# One continuous poster: every section paints its slice of this master ramp,
# so the README reads as a single scene with no GitHub background in between.
SEC_BTN, SEC_RIDGE, SEC_RANGE, SEC_CONTRIB, SEC_LANG, SEC_FIRE = 320, 376, 744, 894, 1062, 1238
SEC_VIDEOS = 1238
CHANNEL_ID = "UCRfvtmLL6FNOKOfDn81rqig"
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt_ym(ym):
    return f"{MONTH_ABBR[int(ym[5:7]) - 1]} {ym[:4]}"


def fmt_date(day):
    return f"{int(day[8:10])} {MONTH_ABBR[int(day[5:7]) - 1]} {day[:4]}"


def cutoff30():
    f = datetime.date.fromisoformat(DATA.get("fetched", "2026-10-04"))
    return (f - datetime.timedelta(days=30)).isoformat()


def esc(x):
    return x.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
RAMP_DARK = [(320, "#0A1A10"), (744, "#08160D"), (1238, "#05110A"), (1560, "#040E09")]
RAMP_LIGHT = [(320, "#EFF5EC"), (744, "#E9F1E5"), (1238, "#DFE9DA"), (1560, "#DCE6D7")]


def bgcol(t, y):
    ramp = RAMP_LIGHT if t["light"] else RAMP_DARK
    if y <= ramp[0][0]:
        return ramp[0][1]
    for (y0, c0), (y1, c1) in zip(ramp, ramp[1:]):
        if y <= y1:
            return lerp_hex(c0, c1, (y - y0) / (y1 - y0))
    return ramp[-1][1]


def section_bg(t, y0, h, w=880):
    c0, c1 = bgcol(t, y0), bgcol(t, y0 + h)
    return (f'<linearGradient id="g_bg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{c0}"/><stop offset="1" stop-color="{c1}"/></linearGradient>'
            f'<rect width="{w}" height="{h}" fill="url(#g_bg)"/>')


def season_particles(p, rng):
    """The sky knows the date: leaves in autumn, snow in winter, petals in
    spring; summer belongs to the fireflies alone."""
    kind = {12: "snow", 1: "snow", 2: "snow", 3: "petal", 4: "petal", 5: "petal",
            6: "ff", 7: "ff", 8: "ff", 9: "leaf", 10: "leaf", 11: "leaf"}[datetime.date.today().month]
    s = ""
    if kind == "leaf":
        col, op = ("#8A5A2B", ".55") if p["star"] else ("#C9823E", ".75")
        for _ in range(7):
            x, dur, dd, fx = rng.uniform(50, 840), rng.uniform(9, 16), rng.uniform(0, 12), rng.uniform(-60, 80)
            s += (f'<g transform="translate({x:.0f},-6)"><g class="fall" '
                  f'style="--d:{dur:.1f}s;--dd:{dd:.1f}s;--fx:{fx:.0f}px">'
                  f'<path d="M0,0 Q3,-3 6,0 Q3,3 0,0 Z" fill="{col}" opacity="{op}"/></g></g>')
    elif kind == "snow":
        for _ in range(12):
            x, dur, dd, fx = rng.uniform(20, 860), rng.uniform(13, 22), rng.uniform(0, 16), rng.uniform(-40, 40)
            s += (f'<g transform="translate({x:.0f},-6)"><g class="fall" '
                  f'style="--d:{dur:.1f}s;--dd:{dd:.1f}s;--fx:{fx:.0f}px">'
                  f'<circle r="{rng.uniform(1.3, 2.4):.1f}" fill="#FFFFFF" opacity=".8"/></g></g>')
    elif kind == "petal":
        for _ in range(9):
            x, dur, dd, fx = rng.uniform(40, 840), rng.uniform(10, 17), rng.uniform(0, 12), rng.uniform(-70, 70)
            s += (f'<g transform="translate({x:.0f},-6)"><g class="fall" '
                  f'style="--d:{dur:.1f}s;--dd:{dd:.1f}s;--fx:{fx:.0f}px">'
                  f'<ellipse rx="2.8" ry="1.7" fill="#EBD8DF" opacity=".8"/></g></g>')
    return s


NAME = "LuixBits"
TAGLINE = "Software Engineer · UX Designer · NixOS"
PROMPT = "luix@forest:~ $ whoami"

WAYPOINTS = [
    ("luix_nix_config", "NixOS as code — flakes, Home Manager.", "nix"),
    ("luixbits-roomplanner.nvim", "Flat planning in Neovim, metric-exact.", "lua"),
    ("TextSight", "Master thesis — AI-mapped connections.", "svelte"),
    ("luixbits-noctalia-plugins", "Plugins for the Noctalia shell.", "luau"),
]
MARKS = [(150, 110), (430, 202), (620, 294), (300, 386)]

STAR_PATH = ("M0,-6.2 L1.9,-1.9 L6.4,-1.5 L3.1,1.6 L4,6.2 L0,3.6 "
             "L-4,6.2 L-3.1,1.6 L-6.4,-1.5 L-1.9,-1.9 Z")


def header(p, fname):
    rng = random.Random(42)
    W, H = 880, 320
    s = svg_open(W, H, f"{NAME} — forest profile header", f"{NAME}. {TAGLINE}.")
    stops = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in p["sky"])
    s += (
        "<defs>"
        f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">{stops}</linearGradient>'
        f'<radialGradient id="g_hor"><stop offset="0" stop-color="{p["horizon"]}" stop-opacity=".55"/>'
        f'<stop offset="1" stop-color="{p["horizon"]}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="g_orb"><stop offset="0" stop-color="{p["orb_glow"]}" stop-opacity=".8"/>'
        f'<stop offset="1" stop-color="{p["orb_glow"]}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="g_ff"><stop offset="0" stop-color="{FIREFLY}" stop-opacity=".85"/>'
        f'<stop offset="1" stop-color="{FIREFLY}" stop-opacity="0"/></radialGradient>'
        f'<filter id="f_name" x="-30%" y="-60%" width="160%" height="220%">'
        f'<feDropShadow dx="0" dy="0" stdDeviation="8" flood-color="{p["name_glow"]}" flood-opacity="{p["glow_op"]}"/></filter>'
        '<filter id="f_mist" x="-5%" y="-300%" width="110%" height="700%">'
        '<feGaussianBlur stdDeviation="7"/></filter>'
        "</defs>"
    )
    s += f'<rect width="{W}" height="{H}" fill="url(#sky)"/>'

    ox, oy, orb_r = 742, 66, p["orb_r"]
    if p["star"]:
        for _ in range(26):
            x, y = rng.uniform(12, 868), rng.uniform(10, 160)
            if (x - ox) ** 2 + (y - oy) ** 2 < 95 ** 2:
                continue
            r = rng.uniform(0.6, 1.3)
            o = rng.uniform(0.2, 0.65)
            if rng.random() < 0.34:
                d, dd = rng.uniform(3.5, 7), rng.uniform(0, 4)
                s += (f'<circle class="tw" style="--d:{d:.1f}s;--dd:{dd:.1f}s" '
                      f'cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{p["star"]}"/>')
            else:
                s += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{p["star"]}" opacity="{o:.2f}"/>'

    s += f'<circle cx="{ox}" cy="{oy}" r="{p["glow_r"]}" fill="url(#g_orb)" opacity="{p["orb_glow_op"]}"/>'
    s += f'<circle cx="{ox}" cy="{oy}" r="{orb_r}" fill="{p["orb"]}"/>'
    if p["star"]:
        # real moon phase: shadow disc offset by illuminated fraction
        illum, waxing = moon_phase()
        s += (f'<circle cx="{ox - 7}" cy="{oy - 3}" r="4" fill="#D3E2CF" opacity=".55"/>'
              f'<circle cx="{ox + 6}" cy="{oy + 7}" r="2.6" fill="#D3E2CF" opacity=".45"/>')
        dx = 2 * orb_r * illum * (-1 if waxing else 1)
        s += (f'<clipPath id="mc"><circle cx="{ox}" cy="{oy}" r="{orb_r}"/></clipPath>'
              f'<circle clip-path="url(#mc)" cx="{ox + dx:.1f}" cy="{oy}" r="{orb_r}" '
              f'fill="#08190F" opacity=".93"/>')
        s += ('<g class="shoot"><line x1="2" y1="-0.7" x2="30" y2="-10" stroke="#DFF0E2" '
              'stroke-width="1.4" stroke-linecap="round" opacity=".7"/>'
              '<circle r="1.7" fill="#FFFFFF"/></g>')
    else:  # morning clouds and birds
        blob = ('<ellipse cx="0" cy="0" rx="46" ry="12"/><ellipse cx="32" cy="5" rx="34" ry="10"/>'
                '<ellipse cx="-30" cy="6" rx="30" ry="9"/>')
        s += (f'<g class="cloud" style="--p:150s"><g transform="translate(0,52)" fill="#FFFFFF" '
              f'opacity=".5">{blob}</g></g>'
              f'<g class="cloud" style="--p:210s;--dd:-90s"><g transform="translate(0,92) scale(.7)" '
              f'fill="#FFFFFF" opacity=".35">{blob}</g></g>')
        for bx, by, sc in ((235, 96, 1.0), (278, 80, 0.78), (322, 110, 0.6)):
            s += (f'<path d="M{bx},{by} q{5.6 * sc:.1f},{-4.8 * sc:.1f} {11.2 * sc:.1f},0 '
                  f'q{5.6 * sc:.1f},{-4.8 * sc:.1f} {11.2 * sc:.1f},0" stroke="{STEM}" '
                  f'stroke-width="{1.5 * sc:.1f}" fill="none" stroke-linecap="round" opacity=".7"/>')

    s += f'<ellipse cx="560" cy="240" rx="470" ry="95" fill="url(#g_hor)" opacity="{p["horizon_op"]}"/>'

    mists = [(216, 18), (242, 20), (272, 24)]
    drift = [(18, 38), (-22, 52), (14, 44)]
    for i, (base, h_rng, w_rng, step, color, op, damp) in enumerate(p["layers"]):
        band_to = p["layers"][i + 1][0] + 10 if i + 1 < len(p["layers"]) else H + 8
        if i == 3 and p["star"]:
            s += ('<g class="hike"><g class="bob">'
                  '<circle cx="0" cy="-12.5" r="2.6" fill="#07130C"/>'
                  '<path d="M-2.8,0 C-3.2,-7.5 3.2,-7.5 2.8,0 Z" fill="#07130C"/>'
                  '<line x1="2.4" y1="-6" x2="7.2" y2="-2.5" stroke="#07130C" stroke-width="1.5"/>'
                  '<circle cx="8" cy="-0.5" r="6.5" fill="url(#g_ff)" opacity=".75"/>'
                  f'<circle cx="8" cy="-0.5" r="1.9" fill="{FIREFLY}"/>'
                  '</g></g>')
        tl = treeline(rng, base, -16, W + 16, h_rng, w_rng, step, color, op, band_to, damp)
        if i < 2:
            tl = f'<g class="sway" style="--p:{14 + i * 5}s">{tl}</g>'
        s += tl
        if i < 3:
            my, mh = mists[i]
            tx, d = drift[i]
            s += (f'<rect class="drift" style="--tx:{tx}px;--d:{d}s" x="-50" y="{my}" '
                  f'width="980" height="{mh}" fill="{p["mist"]}" opacity="{p["mist_ops"][i]}" '
                  f'filter="url(#f_mist)"/>')

    if p["star"]:
        zones = [((66, 440), (238, 296), 6), ((500, 846), (180, 296), 7)]
        for (xa, xb), (ya, yb), n in zones:
            for _ in range(n):
                x, y = rng.uniform(xa, xb), rng.uniform(ya, yb)
                tx = rng.uniform(5, 11) * rng.choice((-1, 1))
                ty = rng.uniform(3, 8) * rng.choice((-1, 1))
                d, dd = rng.uniform(5.5, 11), rng.uniform(0, 6)
                rc = rng.uniform(1.3, 2.0)
                s += (f'<g transform="translate({x:.1f} {y:.1f})">'
                      f'<g class="ffw" style="--tx:{tx:.1f}px;--ty:{ty:.1f}px;--d:{d:.1f}s;--dd:{dd:.1f}s">'
                      f'<circle class="ffp" style="--p:{d * .55:.1f}s;--dd:{dd:.1f}s" r="{rc * 3.4:.1f}" fill="url(#g_ff)"/>'
                      f'<circle class="ffp" style="--p:{d * .55:.1f}s;--dd:{dd:.1f}s" r="{rc:.1f}" fill="{FF_CORE}"/>'
                      f"</g></g>")
    else:
        for _ in range(6):
            x, y = rng.uniform(90, 790), rng.uniform(120, 264)
            d, dd = rng.uniform(5, 9), rng.uniform(0, 5)
            s += (f'<circle class="mote" style="--p:{d:.1f}s;--dd:{dd:.1f}s" cx="{x:.1f}" cy="{y:.1f}" '
                  f'r="{rng.uniform(1.2, 2.0):.1f}" fill="#FFFFFF"/>')
        s += ('<g><animateMotion dur="28s" repeatCount="indefinite" rotate="0" '
              'path="M310,185 C430,120 560,215 480,150 C415,100 340,220 310,185 Z"/>'
              '<g class="flut"><path d="M0,0 L-6.5,-4.5 L-5,2.2 Z" fill="#D08057"/>'
              '<path d="M0,0 L6.5,-4.5 L5,2.2 Z" fill="#C06A44"/></g></g>')

    if not p["star"]:  # morning fog floor, so the poster continues seamlessly below
        s += ('<rect x="-10" y="288" width="900" height="20" fill="#EFF5EC" opacity=".85" '
              'filter="url(#f_mist)"/>'
              '<rect x="-10" y="304" width="900" height="16" fill="#EFF5EC"/>')
    s += (
        f'<text x="56" y="170" font-size="38" font-weight="700" letter-spacing="0.5" '
        f'fill="{p["name"]}" filter="url(#f_name)">{NAME}</text>'
        f'<text x="56" y="196" font-size="13" letter-spacing="0.3" fill="{p["tagline"]}">{TAGLINE}</text>'
    )
    s += season_particles(p, rng)
    (OUT / fname).write_text(s + "</svg>")


def button(t, base, kind, label, grey=False, note=None):
    W, H = 220, 56
    s = svg_open(W, H, label, f"{label} link button.")
    s += section_bg(t, SEC_BTN, H, w=W)
    if grey:
        box, line, ink, icon = t["gbox"], t["gline"], t["gink"], t["gink"]
    else:
        box, line, ink, icon = t["bbox"], t["bline"], t["bink"], t["icon"]
    s += f'<rect x="4" y="8" width="212" height="40" rx="6" fill="{box}" stroke="{line}" stroke-width="1.5"/>'
    if kind == "pine":
        s += pines_g(28, 40, 20, 7.5, icon)
    elif kind == "play":
        s += (f'<rect x="20" y="21" width="19" height="13" rx="3" fill="none" stroke="{icon}" stroke-width="1.6"/>'
              f'<polygon points="27.3,24.7 27.3,30.3 32.5,27.5" fill="{icon}"/>')
    elif kind == "heart":
        hc = icon if grey else t["gold"]
        fill = "none" if grey else hc
        stroke = f' stroke="{hc}" stroke-width="1.6"' if grey else ""
        s += (f'<path transform="translate(20,21) scale(.85)" fill="{fill}"{stroke} '
              'd="M9 15.5 C4 11.6 1 9 1 5.7 A3.9 3.9 0 0 1 9 4.3 A3.9 3.9 0 0 1 17 5.7 C17 9 14 11.6 9 15.5 Z"/>')
    elif kind == "mail":
        s += (f'<rect x="20" y="21.5" width="18" height="12" rx="2" fill="none" stroke="{icon}" stroke-width="1.6"/>'
              f'<path d="M22,23.5 L29,29 L36,23.5" fill="none" stroke="{icon}" stroke-width="1.6" stroke-linejoin="round"/>')
    s += f'<text x="50" y="33" font-size="13.5" fill="{ink}">{label}</text>'
    if note:
        s += f'<text x="204" y="33" font-size="11" text-anchor="end" fill="{t["gsuf"]}">{note}</text>'
    (OUT / f"{base}{t['sfx']}.svg").write_text(s + "</svg>")


def _month_add(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    m += k
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return f"{y:04d}-{m:02d}"


def _month_range(a, b):
    out = []
    while a <= b:
        out.append(a)
        a = _month_add(a, 1)
    return out


def star_ridges(t):
    """jdx's trending charts, restyled: each row is a repo's real cumulative
    star history drawn as a mountain ridgeline with pines on it. The line
    draws itself in, then a firefly wanders the ridge forever (SMIL
    animateMotion along the same path). One SVG per row = one link per repo."""
    W, H = 880, 92
    hist = DATA.get("star_history", {})
    end_m = DATA.get("fetched", "2026-10")[:7]
    for i, (name, desc, _lang) in enumerate(WAYPOINTS):
        stars = DATA["stars"].get(name, 0)
        h = hist.get(name, {})
        months = _month_range(h.get("created", end_m)[:7], end_m)
        starred = h.get("starred", [])
        vals = [sum(1 for s_ in starred if s_[:7] <= m) for m in months]
        if len(months) > 36:
            months, vals = months[-36:], vals[-36:]
        while len(vals) < 6:
            months.insert(0, _month_add(months[0], -1))
            vals.insert(0, 0)
        vmax = max(vals[-1], 1)

        x0, x1, base, hmax = 350, 806, 72, 46
        dx = (x1 - x0) / (len(vals) - 1)
        pts = [(x0 + k * dx, base - (v / vmax) * hmax) for k, v in enumerate(vals)]
        line_d = smooth_path(pts)
        area_d = line_d + f" L{x1},{base} L{x0},{base} Z"
        plen = sum(math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1)) * 1.15

        s = svg_open(W, H, name, f"{name}: {desc} Cumulative stars since "
                                 f"{months[0]}, now {stars}.")
        s += (f'<linearGradient id="g_a" x1="0" y1="0" x2="0" y2="1">'
              f'<stop offset="0" stop-color="{t["icon"]}" stop-opacity=".28"/>'
              f'<stop offset="1" stop-color="{t["icon"]}" stop-opacity="0"/></linearGradient>'
              f'<radialGradient id="g_rg"><stop offset="0" stop-color="{FIREFLY}" stop-opacity=".8"/>'
              f'<stop offset="1" stop-color="{FIREFLY}" stop-opacity="0"/></radialGradient>')
        s += section_bg(t, SEC_RIDGE + i * 92, H)
        if i < 3:
            s += (f'<rect x="0" y="{H - 1}" width="880" height="1" '
                  f'fill="{"#D6E1D2" if t["light"] else "#102416"}"/>')
        s += (f'<text x="34" y="38" font-size="15" font-weight="700" fill="{t["ink"]}">{name}</text>'
              f'<text x="34" y="58" font-size="11.5" fill="{t["dim"]}">{desc}</text>')
        s += f'<g class="fade" style="--dd:{1.1 + i * .25:.2f}s"><path d="{area_d}" fill="url(#g_a)"/></g>'
        s += (f'<path id="rp" class="draw" style="--len:{plen:.0f};--dd:{.25 + i * .25:.2f}s;'
              f'stroke-dasharray:{plen:.0f}" d="{line_d}" fill="none" '
              f'stroke="{t["icon"]}" stroke-width="2" stroke-linecap="round"/>')
        ridge_pines = ""
        for k in range(2, len(pts) - 2, 3):
            px, py = pts[k]
            ridge_pines += "".join(
                f'<polygon points="{q}"/>' for q in pine(px, py + 1, 5.5, 2.6, tiers=1))
        s += (f'<g class="fade" style="--dd:{1.4 + i * .25:.2f}s" fill="{t["tree2"]}">'
              f"{ridge_pines}</g>")
        lx, ly = pts[-1]
        s += (f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="7" fill="url(#g_rg)" class="ffp" '
              f'style="--p:3.4s"/>'
              f'<path transform="translate({lx:.1f},{ly - 1:.1f}) scale(.65)" d="{STAR_PATH}" '
              f'fill="{t["gold"]}"/>')
        tracer = FIREFLY if not t["light"] else t["gold"]
        s += (f'<circle r="1.7" fill="{tracer}" opacity=".9">'
              f'<animateMotion dur="{11 + i * 2.5:.0f}s" begin="{2.6 + i * .25:.2f}s" '
              f'repeatCount="indefinite"><mpath href="#rp" xlink:href="#rp"/></animateMotion></circle>')
        s += f'<text x="{lx + 13:.0f}" y="{ly + 4.5:.0f}" font-size="12.5" fill="{t["ink"]}">{stars}</text>'
        n30 = sum(1 for s_ in h.get("starred", []) if s_ >= cutoff30())
        if n30:
            s += (f'<text x="846" y="{ly + 18:.0f}" font-size="9" text-anchor="end" '
                  f'fill="{t["faint"]}">+{n30} in 30d</text>')
        s += (f'<text x="{x0}" y="86" font-size="9" fill="{t["faint"]}">{fmt_ym(months[0])}</text>'
              f'<text x="{x1}" y="86" font-size="9" text-anchor="end" '
              f'fill="{t["faint"]}">{fmt_ym(months[-1])}</text>')
        (OUT / f"ridge-{i + 1}{t['sfx']}.svg").write_text(s + "</svg>")


def star_range(t):
    """jdx's cumulative chart ("beyond mise") restyled: every star across all
    public repos as one mountain range, with an echo ridge behind for depth."""
    W, H = 880, 150
    rh = DATA.get("range_history", {})
    dates = rh.get("starred", [])
    total = rh.get("total", len(dates))
    end_m = DATA.get("fetched", "2026-10")[:7]
    months = _month_range(dates[0][:7] if dates else end_m, end_m)
    if len(months) > 48:
        months = months[-48:]
    while len(months) < 6:
        months.insert(0, _month_add(months[0], -1))
    vals = [sum(1 for s_ in dates if s_[:7] <= m) for m in months]
    vmax = max(vals) or 1

    x0, x1, base, hmax = 34, 846, 128, 96
    dx = (x1 - x0) / (len(vals) - 1)
    pts = [(x0 + k * dx, base - (v / vmax) * hmax) for k, v in enumerate(vals)]
    line_d = smooth_path(pts)
    area_d = line_d + f" L{x1},{base} L{x0},{base} Z"
    plen = sum(math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1)) * 1.15

    s = svg_open(W, H, "The range",
                 f"Cumulative stars across all public repos since {months[0]}: {total}.")
    s += section_bg(t, SEC_RANGE, H)
    s += (f'<linearGradient id="g_a" x1="0" y1="0" x2="0" y2="1">'
          f'<stop offset="0" stop-color="{t["icon"]}" stop-opacity=".3"/>'
          f'<stop offset="1" stop-color="{t["icon"]}" stop-opacity="0"/></linearGradient>'
          f'<radialGradient id="g_rg"><stop offset="0" stop-color="{FIREFLY}" stop-opacity=".8"/>'
          f'<stop offset="1" stop-color="{FIREFLY}" stop-opacity="0"/></radialGradient>')
    echo = "".join(f"{x + 14:.1f},{base - (base - y) * .52:.1f} " for x, y in pts)
    s += (f'<polygon points="{x0 + 14},{base} {echo}{x1 + 14},{base}" '
          f'fill="{"#BCD2BF" if t["light"] else "#122A1B"}" opacity=".65"/>')
    s += f'<g class="fade" style="--dd:1.2s"><path d="{area_d}" fill="url(#g_a)"/></g>'
    s += (f'<path id="rp" class="draw" style="--len:{plen:.0f};--dd:.3s;'
          f'stroke-dasharray:{plen:.0f}" d="{line_d}" fill="none" '
          f'stroke="{t["icon"]}" stroke-width="2" stroke-linecap="round"/>')
    pines = ""
    for k in range(2, len(pts) - 2, 4):
        px, py = pts[k]
        pines += "".join(f'<polygon points="{q}"/>' for q in pine(px, py + 1, 6, 2.8, tiers=1))
    s += f'<g class="fade" style="--dd:1.5s" fill="{t["tree2"]}">{pines}</g>'
    lx, ly = pts[-1]
    s += (f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="8" fill="url(#g_rg)" class="ffp" style="--p:3.8s"/>'
          f'<path transform="translate({lx:.1f},{ly - 1:.1f}) scale(.75)" d="{STAR_PATH}" fill="{t["gold"]}"/>'
          f'<text x="{lx - 14:.0f}" y="{ly - 10:.0f}" font-size="13" text-anchor="end" '
          f'fill="{t["ink"]}">{total}</text>')
    n30 = sum(1 for s_ in dates if s_ >= cutoff30())
    if n30:
        s += (f'<text x="{lx - 14:.0f}" y="{ly - 24:.0f}" font-size="9" text-anchor="end" '
              f'fill="{t["faint"]}">+{n30} in 30d</text>')
    s += (f'<text x="{x0}" y="142" font-size="9" fill="{t["faint"]}">{fmt_ym(months[0])}</text>'
          f'<text x="{x1}" y="142" font-size="9" text-anchor="end" '
          f'fill="{t["faint"]}">{fmt_ym(months[-1])}</text>')
    s += (f'<circle r="1.7" fill="{FIREFLY if not t["light"] else t["gold"]}" opacity=".9">'
          f'<animateMotion dur="16s" begin="2.8s" repeatCount="indefinite">'
          f'<mpath href="#rp" xlink:href="#rp"/></animateMotion></circle>')
    if not t["light"]:
        s += (f'<circle class="ffp" style="--p:5.6s;--dd:2.2s" cx="150" cy="40" r="1.5" fill="{FIREFLY}"/>')
    (OUT / f"range{t['sfx']}.svg").write_text(s + "</svg>")


def contribution_forest(t):
    rng = random.Random(11)
    W, H = 880, 168
    base_y = 150
    vals = DATA["calendar"]
    maxv, total = max(vals), DATA["cal_total"]

    s = svg_open(W, H, "Contribution forest",
                 f"One pine per day over the last year; {total} contributions.")
    s += section_bg(t, SEC_CONTRIB, H)

    step = 812 / (len(vals) - 1)
    tops = []
    trees = ""
    for i, v in enumerate(vals):
        x = 34 + i * step
        it = math.log(1 + v) / math.log(1 + maxv) if maxv else 0
        h = 2.5 + it * 86
        w = 4.5 + it * 6.5
        color = lerp_hex(t["lerp0"], t["lerp1"], it)
        tiers = 3 if h >= 26 else (2 if h >= 10 else 1)
        shapes = "".join(f'<polygon points="{p}"/>' for p in pine(x, base_y, h, w, tiers=tiers))
        trees += f'<g fill="{color}">{shapes}</g>'
        tops.append((v, x, base_y - h))
    s += trees
    s += f'<rect x="30" y="{base_y}" width="820" height="2" rx="1" fill="{t["ground"]}"/>'
    end_ym = DATA.get("fetched", "2026-10")[:7]
    s += (f'<text x="34" y="162" font-size="10" fill="{t["faint"]}">{total:,} contributions</text>'
          f'<text x="846" y="162" font-size="10" text-anchor="end" fill="{t["faint"]}">'
          f'{fmt_ym(_month_add(end_ym, -12))} → {fmt_ym(end_ym)}</text>')
    s += ('<filter id="f_fog" x="-10%" y="-200%" width="120%" height="500%">'
          '<feGaussianBlur stdDeviation="6"/></filter>')
    fog = "#B9D6C1" if not t["light"] else "#FFFFFF"
    fog_op = ".05" if not t["light"] else ".3"
    s += (f'<rect class="drift" style="--tx:24px;--d:46s" x="20" y="118" width="840" height="26" '
          f'fill="{fog}" opacity="{fog_op}" filter="url(#f_fog)"/>')
    for v, x, ty in sorted(tops, reverse=True)[:4]:
        if t["ff"]:
            d = rng.uniform(3.5, 6)
            s += (f'<circle class="ffp" style="--p:{d:.1f}s;--dd:{rng.uniform(0, 3):.1f}s" '
                  f'cx="{x:.1f}" cy="{ty - 6:.1f}" r="1.5" fill="{FIREFLY}"/>')
        else:
            s += f'<circle cx="{x:.1f}" cy="{ty - 6:.1f}" r="1.5" fill="{t["gold"]}" opacity=".7"/>'

    (OUT / f"contribution-forest{t['sfx']}.svg").write_text(s + "</svg>")


def languages(t):
    W, H = 880, 176
    langs = DATA["langs"]
    total = sum(langs.values())
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    rows = [(k, v / total) for k, v in top]
    rows.append(("other", (total - sum(v for _, v in top)) / total))
    s = svg_open(W, H, "Languages", "Language share across all public repos, by bytes of source.")
    s += section_bg(t, SEC_LANG, H)
    for k, (name, share) in enumerate(rows):
        y = 42 + k * 22
        color = LANG_COLORS.get(name, OTHER_COLOR)
        s += (f'<text x="40" y="{y}" font-size="11.5" fill="{t["ink"]}">{name}</text>'
              f'<rect x="150" y="{y - 7}" width="620" height="8" rx="2" fill="{t["ink"]}" opacity=".08"/>'
              f'<rect class="grow" style="--dd:{k * .12:.2f}s" x="150" y="{y - 7}" '
              f'width="{max(3, 620 * share):.1f}" height="8" rx="2" fill="{color}"/>'
              f'<text x="846" y="{y}" font-size="11" text-anchor="end" fill="{t["dim"]}">{share * 100:.1f}%</text>')
    s += (f'<text x="846" y="166" font-size="9.5" text-anchor="end" fill="{t["faint"]}">'
          f'{DATA.get("n_repos", 29)} public repos · {total / 1e6:.1f} MB of source</text>')
    if not t["light"]:
        for fx, fy, fp, fd in ((612, 164, 5.2, 1.1), (247, 168, 6.4, 3.0)):
            s += (f'<circle class="ffp" style="--p:{fp}s;--dd:{fd}s" cx="{fx}" cy="{fy}" '
                  f'r="1.5" fill="{FIREFLY}"/>')
    (OUT / f"languages{t['sfx']}.svg").write_text(s + "</svg>")


def videos(t):
    """jdx's writing section, pointed at the YouTube channel: latest uploads
    as clickable rows, title and date only."""
    vids = DATA.get("videos", [])[:3]
    for i, v in enumerate(vids):
        W, H = 880, 54
        s = svg_open(W, H, esc(v["title"]), f"YouTube video, published {fmt_date(v['published'])}.")
        s += section_bg(t, SEC_VIDEOS + i * 54, H)
        if i < len(vids) - 1:
            s += (f'<rect x="0" y="{H - 1}" width="880" height="1" '
                  f'fill="{"#D6E1D2" if t["light"] else "#102416"}"/>')
        s += (f'<rect x="34" y="14" width="26" height="26" rx="6" fill="{t["inset"]}" '
              f'stroke="{t["iline"]}" stroke-width="1.25"/>'
              f'<polygon points="44,21.5 44,32.5 53,27" fill="{t["icon"]}"/>')
        title = v["title"]
        if len(title) > 66:
            title = title[:65] + "…"
        s += f'<text x="74" y="31.5" font-size="13" fill="{t["ink"]}">{esc(title)}</text>'
        s += (f'<text x="846" y="31.5" font-size="10" text-anchor="end" '
              f'fill="{t["faint"]}">{fmt_date(v["published"])}</text>')
        (OUT / f"videos-{i + 1}{t['sfx']}.svg").write_text(s + "</svg>")


def campfire(t):
    W, H = 880, 120
    s = svg_open(W, H, "Campfire", "A campsite. At night the fire burns; by day, smoke and birds.")
    s += section_bg(t, SEC_FIRE, H)
    s += f'<rect x="24" y="94" width="832" height="1.5" fill="{t["ground"]}"/>'
    s += (f'<polygon points="192,94 230,48 268,94" fill="{t["inset"]}" stroke="{t["iline"]}" stroke-width="1.5"/>'
          f'<line x1="230" y1="48" x2="230" y2="94" stroke="{t["iline"]}" stroke-width="1.2"/>'
          f'<polyline points="220,94 230,72 240,94" fill="none" stroke="{t["iline"]}" stroke-width="1.2"/>')
    s += (pines_g(560, 94, 26, 9, t["tree1"]) + pines_g(592, 94, 17, 6.5, t["tree2"], tiers=2)
          + pines_g(676, 94, 22, 7.5, t["tree1"]) + pines_g(706, 94, 14, 5.5, t["tree2"], tiers=2)
          + pines_g(744, 94, 19, 7, t["tree1"], tiers=2))
    s += (f'<rect x="-14" y="-2.5" width="28" height="5" rx="2" transform="translate(330,92) rotate(18)" fill="{CRACK}"/>'
          f'<rect x="-14" y="-2.5" width="28" height="5" rx="2" transform="translate(330,92) rotate(-18)" fill="{CRACK}"/>')
    if t["ff"]:
        s += ('<radialGradient id="g_fire"><stop offset="0" stop-color="#FFD36E" stop-opacity=".55"/>'
              '<stop offset="1" stop-color="#FFD36E" stop-opacity="0"/></radialGradient>'
              '<circle cx="330" cy="76" r="36" fill="url(#g_fire)"/>')
        s += ('<g transform="translate(330,89)">'
              '<path class="fl" style="--fd:.95s" d="M0,0 C-9,-9 -7,-21 0,-30 C7,-21 9,-9 0,0" fill="#D9A441"/>'
              '<path class="fl" style="--fd:1.25s" d="M0,0 C-6,-6 -4.8,-14 0,-20 C4.8,-14 6,-6 0,0" fill="#FFD36E"/>'
              '<path class="fl" style="--fd:.8s" d="M0,0 C-3.5,-4 -2.8,-8.5 0,-12 C2.8,-8.5 3.5,-4 0,0" fill="#FFF2C9"/>'
              "</g>")
        for sx, dd_, dl in ((323, 2.4, 0.3), (330, 3.1, 1.2), (337, 2.7, 0.7), (327, 3.5, 2.0)):
            s += (f'<circle class="spk" style="--d:{dd_}s;--dd:{dl}s" cx="{sx}" cy="62" r="1.2" '
                  f'fill="{FIREFLY}"/>')
        for pr, pp, pdd in ((4, 5.2, 0), (5, 6.6, 1.8), (6, 8, 3.6)):
            s += (f'<circle class="puff" style="--p:{pp}s;--dd:{pdd}s" cx="330" cy="52" r="{pr}" '
                  f'fill="#9CB9A4"/>')
        s += ('<g transform="translate(676,64)">'
              '<path d="M-3.5,-4.5 L-2,-8 L-.5,-4.8 Z" fill="#1E4530"/>'
              '<path d="M.5,-4.8 L2,-8 L3.5,-4.5 Z" fill="#1E4530"/>'
              '<ellipse cx="0" cy="0" rx="4" ry="5.2" fill="#1E4530"/>'
              '<g class="owl" style="--dd:2s">'
              f'<circle cx="-1.5" cy="-1.5" r=".9" fill="{FIREFLY}"/>'
              f'<circle cx="1.5" cy="-1.5" r=".9" fill="{FIREFLY}"/></g></g>')
    else:
        s += (f'<path class="smoke" d="M330,86 C322,70 340,58 332,42 C326,30 334,22 330,10" '
              f'fill="none" stroke="{t["dim"]}" stroke-width="2" stroke-linecap="round" opacity=".4"/>')
        for bx, by, sc in ((560, 40, 0.9), (604, 28, 0.7)):
            s += (f'<path d="M{bx},{by} q{5.6 * sc:.1f},{-4.8 * sc:.1f} {11.2 * sc:.1f},0 '
                  f'q{5.6 * sc:.1f},{-4.8 * sc:.1f} {11.2 * sc:.1f},0" stroke="{STEM}" '
                  f'stroke-width="{1.4 * sc:.1f}" fill="none" stroke-linecap="round" opacity=".6"/>')
    (OUT / f"campfire{t['sfx']}.svg").write_text(s + "</svg>")


# ---------------------------------------------------------------- data
def gh_json(url, tok, payload=None, accept=None):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "forest-profile"})
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    if accept:
        req.add_header("Accept", accept)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(payload).encode()
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_live():
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    path = HERE / "data.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    try:
        data["stars"] = {r: gh_json(f"https://api.github.com/repos/{LOGIN}/{r}", tok)["stargazers_count"]
                         for r in FEATURED}
    except Exception as e:
        print("stars fetch failed, keeping old:", e)
    try:
        repos = [x["name"] for x in gh_json(f"https://api.github.com/users/{LOGIN}/repos?per_page=100", tok)
                 if not x["fork"]]
        agg = {}
        for r in repos:
            for k, v in gh_json(f"https://api.github.com/repos/{LOGIN}/{r}/languages", tok).items():
                agg[k] = agg.get(k, 0) + v
        if agg:
            data["langs"] = agg
            data["n_repos"] = len(repos)
    except Exception as e:
        print("languages fetch failed, keeping old:", e)
    try:
        hist = {}
        for r in FEATURED:
            created = gh_json(f"https://api.github.com/repos/{LOGIN}/{r}", tok)["created_at"][:10]
            starred = []
            for page in range(1, 5):
                batch = gh_json(f"https://api.github.com/repos/{LOGIN}/{r}/stargazers"
                                f"?per_page=100&page={page}", tok,
                                accept="application/vnd.github.star+json")
                starred += [x["starred_at"][:10] for x in batch]
                if len(batch) < 100:
                    break
            hist[r] = {"created": created, "starred": sorted(starred)}
        data["star_history"] = hist
    except Exception as e:
        print("star history fetch failed, keeping old:", e)
    if tok:
        try:
            q = ("query($login:String!){user(login:$login){contributionsCollection{"
                 "contributionCalendar{totalContributions weeks{contributionDays{contributionCount}}}}}}")
            cal = gh_json("https://api.github.com/graphql", tok,
                          {"query": q, "variables": {"login": LOGIN}})
            cc = cal["data"]["user"]["contributionsCollection"]["contributionCalendar"]
            data["calendar"] = [d["contributionCount"] for w in cc["weeks"] for d in w["contributionDays"]]
            data["cal_total"] = cc["totalContributions"]
        except Exception as e:
            print("calendar fetch failed, keeping old:", e)
    try:
        import urllib.request
        import xml.etree.ElementTree as ET
        req = urllib.request.Request(
            f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}",
            headers={"User-Agent": "forest-profile"})
        with urllib.request.urlopen(req, timeout=30) as r:
            root = ET.fromstring(r.read())
        ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
        vids = [{"title": e.find("a:title", ns).text,
                 "id": e.find("yt:videoId", ns).text,
                 "published": e.find("a:published", ns).text[:10]}
                for e in root.findall("a:entry", ns)[:3]]
        if vids:
            data["videos"] = vids
    except Exception as e:
        print("videos fetch failed, keeping old:", e)
    data["fetched"] = datetime.date.today().isoformat()
    path.write_text(json.dumps(data))
    print("data.json refreshed", data["fetched"])


def _pic(base, alt, width):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/{base}.svg">'
            f'<img src="assets/{base}-light.svg" width="{width}" align="top" alt="{esc(alt)}"></picture>')


def build_readme():
    hist = DATA.get("star_history", {})
    rh = DATA.get("range_history", {})
    end_ym = DATA.get("fetched", "2026-10")[:7]
    out = ["<!-- One continuous poster: pre-rendered SVG slices of a single scene, drawn by",
           "     generate.py from real data and regenerated nightly by forest.yml.",
           "     Architecture after jdx/jdx. The forest art is original. -->",
           '<p align="center">',
           '<picture><source media="(prefers-color-scheme: dark)" srcset="assets/header-dark.svg">'
           '<img src="assets/header-light.svg" width="100%" align="top" alt="LuixBits — Software Engineer '
           '· UX Designer · NixOS. A forest under the real moon phase, with the season\'s weather."></picture>',
           _pic("link-site", "luizperren.dev — coming soon", "25%")
           + '<a href="https://www.youtube.com/@LuixBits">' + _pic("link-youtube", "YouTube", "25%") + "</a>"
           + '<a href="https://www.doctorswithoutborders.org/">'
           + _pic("link-sponsor", "Sponsor — greyed out for now; the link forwards to Doctors Without Borders", "25%") + "</a>"
           + '<a href="mailto:contact@luizperren.dev">' + _pic("link-contact", "Contact", "25%") + "</a>"]
    for i, (name, desc, _lang) in enumerate(WAYPOINTS):
        created = hist.get(name, {}).get("created", end_ym)[:7]
        alt = (f"{name} — {desc} Star ridge: cumulative stars since {fmt_ym(created)}, "
               f"now {DATA['stars'].get(name, 0)}.")
        out.append(f'<a href="https://github.com/{LOGIN}/{name}">' + _pic(f"ridge-{i + 1}", alt, "100%") + "</a>")
    first = rh.get("starred", [end_ym + "-01"])[0][:7]
    out.append(_pic("range", f"The range: {rh.get('total', 0)} cumulative stars across all public repos "
                             f"since {fmt_ym(first)}, drawn as a mountain panorama.", "100%"))
    out.append(_pic("contribution-forest", f"Contribution forest: one pine per day, {DATA.get('cal_total', 0):,} "
                                           f"contributions from {fmt_ym(_month_add(end_ym, -12))} to {fmt_ym(end_ym)}.", "100%"))
    out.append(_pic("languages", "Languages by bytes across all public repos: Lua 52%, Svelte 19%, "
                                 "TypeScript, Nix, Vue.", "100%"))
    for i, v in enumerate(DATA.get("videos", [])[:3]):
        out.append(f'<a href="https://www.youtube.com/watch?v={v["id"]}">'
                   + _pic(f"videos-{i + 1}", f"Video: {v['title']} ({fmt_date(v['published'])})", "100%") + "</a>")
    out.append(_pic("campfire", "A campsite: tent, campfire, pines and a blinking owl. "
                                "The fire burns at night; by day, smoke and birds.", "100%"))
    out.append("</p>")
    out.append("""
<details><summary>more stats</summary>
<br>
<p align="center">
<img src="https://komarev.com/ghpvc/?username=LuixBits&color=4f8a63&style=flat-square&label=Profile+views" alt="Profile views"><br><br>
<img src="https://streak-stats.demolab.com?user=LuixBits&hide_border=true&background=0A1C12&ring=6BBF7B&fire=D9A441&currStreakLabel=6BBF7B&sideLabels=9CB9A4&currStreakNum=ECF5EC&sideNums=ECF5EC&dates=6F8F7B" alt="GitHub streak"><br><br>
<img src="metrics.svg" alt="Detailed metrics, regenerated daily">
</p>
</details>""")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    if "--fetch" in sys.argv:
        fetch_live()
        sys.exit(0)
    OUT = HERE
    if "--out" in sys.argv:
        OUT = pathlib.Path(sys.argv[sys.argv.index("--out") + 1])
    OUT.mkdir(parents=True, exist_ok=True)
    DATA = json.loads((HERE / "data.json").read_text())
    if DATA.get("videos"):
        SEC_FIRE = SEC_VIDEOS + 54 * min(3, len(DATA["videos"]))

    header(NIGHT, "header-dark.svg")
    header(DAY, "header-light.svg")
    for t in (T_DARK, T_LIGHT):
        button(t, "link-site", "pine", "luizperren.dev", grey=True, note="soon")
        button(t, "link-youtube", "play", "YouTube")
        button(t, "link-sponsor", "heart", "Sponsor", grey=True, note="\u2192 MSF")
        button(t, "link-contact", "mail", "Contact")
        star_ridges(t)
        star_range(t)
        videos(t)
        contribution_forest(t)
        languages(t)
        campfire(t)
    if "--readme" in sys.argv:
        rp = pathlib.Path(sys.argv[sys.argv.index("--readme") + 1])
        rp.write_text(build_readme())
        print("wrote", rp)
    print("rendered:", len(list(OUT.glob("*.svg"))), "SVGs in", OUT)
