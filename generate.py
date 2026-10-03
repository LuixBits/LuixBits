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
    "@keyframes tw{from{opacity:.12}to{opacity:.75}}"
    "@keyframes dr{to{transform:translateX(var(--tx,20px))}}"
    "@keyframes ffd{to{transform:translate(var(--tx,10px),var(--ty,-8px))}}"
    "@keyframes ffp{from{opacity:.12}to{opacity:1}}"
    "@keyframes mt{from{opacity:.05}to{opacity:.4}}"
    "@keyframes bl{to{visibility:hidden}}"
    "@keyframes flm{from{transform:scaleY(.93)}to{transform:scaleY(1.07)}}"
    "@keyframes spk{0%{transform:translateY(0);opacity:.85}100%{transform:translateY(-30px);opacity:0}}"
    "@keyframes smk{from{opacity:.22}to{opacity:.55}}"
    "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
)


def svg_open(w, h, title, desc):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
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
    prompt="#7FA98C", name="#EDF6ED", name_glow="#7FD6A0", glow_op=0.35, tagline="#A9C4B1",
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
    prompt="#4F8A63", name="#12251A", name_glow="#86B894", glow_op=0.25, tagline="#3C5346",
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
    else:
        for bx, by, sc in ((235, 96, 1.0), (278, 80, 0.78), (322, 110, 0.6)):
            s += (f'<path d="M{bx},{by} q{5.6 * sc:.1f},{-4.8 * sc:.1f} {11.2 * sc:.1f},0 '
                  f'q{5.6 * sc:.1f},{-4.8 * sc:.1f} {11.2 * sc:.1f},0" stroke="{STEM}" '
                  f'stroke-width="{1.5 * sc:.1f}" fill="none" stroke-linecap="round" opacity=".7"/>')

    s += f'<ellipse cx="560" cy="240" rx="470" ry="95" fill="url(#g_hor)" opacity="{p["horizon_op"]}"/>'

    mists = [(216, 18), (242, 20), (272, 24)]
    drift = [(18, 38), (-22, 52), (14, 44)]
    for i, (base, h_rng, w_rng, step, color, op, damp) in enumerate(p["layers"]):
        band_to = p["layers"][i + 1][0] + 10 if i + 1 < len(p["layers"]) else H + 8
        s += treeline(rng, base, -16, W + 16, h_rng, w_rng, step, color, op, band_to, damp)
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

    s += (
        f'<text x="56" y="118" font-size="13" fill="{p["prompt"]}">{PROMPT}'
        f'<tspan class="blink"> █</tspan></text>'
        f'<text x="56" y="176" font-size="52" font-weight="700" letter-spacing="1" '
        f'fill="{p["name"]}" filter="url(#f_name)">{NAME}</text>'
        f'<text x="56" y="206" font-size="14.5" letter-spacing="0.4" fill="{p["tagline"]}">{TAGLINE}</text>'
    )
    (OUT / fname).write_text(s + "</svg>")


def button(t, base, kind, label, grey=False):
    W, H = 214, 56
    s = svg_open(W, H, label, f"{label} link button.")
    if grey:
        box, line, ink, icon = t["gbox"], t["gline"], t["gink"], t["gink"]
    else:
        box, line, ink, icon = t["bbox"], t["bline"], t["bink"], t["icon"]
    s += f'<rect x="1" y="8" width="212" height="40" rx="6" fill="{box}" stroke="{line}" stroke-width="1.5"/>'
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
    if grey:
        s += f'<text x="198" y="33" font-size="11" text-anchor="end" fill="{t["gsuf"]}">→ MSF</text>'
    (OUT / f"{base}{t['sfx']}.svg").write_text(s + "</svg>")


def trail_scene(t):
    rng = random.Random(7)
    s = f'<rect x="1" y="1" width="878" height="478" rx="10" fill="{t["panel"]}" stroke="{t["pline"]}" stroke-width="1.5"/>'
    for y0 in (70, 140, 210, 290, 360, 430):
        pts = [(16 + k * (848 / 6), y0 + rng.uniform(-16, 16)) for k in range(7)]
        s += (f'<path d="{smooth_path(pts)}" fill="none" stroke="{t["ink"]}" '
              f'stroke-width="1" opacity="{t["contour_op"]}"/>')
    creek = [(742, 4), (694, 92), (726, 180), (628, 266), (520, 332), (414, 398), (236, 442), (80, 474)]
    cd = smooth_path(creek)
    s += f'<path d="{cd}" fill="none" stroke="{t["creek"]}" stroke-width="7" opacity="{t["creek_op"] * 0.25:.2f}"/>'
    s += f'<path d="{cd}" fill="none" stroke="{t["creek"]}" stroke-width="2.5" opacity="{t["creek_op"]}"/>'
    tr = [(90, 466), (210, 424), MARKS[3], (470, 336), MARKS[2], (545, 244), MARKS[1],
          (268, 152), MARKS[0], (242, 62), (470, 34), (690, 26)]
    s += (f'<path d="{smooth_path(tr)}" fill="none" stroke="{t["trail"]}" stroke-width="2.5" '
          f'stroke-dasharray="1 8" stroke-linecap="round" opacity=".85"/>')

    zones = [(10, 6, 860, 56), (756, 2, 120, 62), (6, 434, 868, 44), (788, 70, 86, 356)]
    for i, (mx, my) in enumerate(MARKS):
        zones.append((mx - 18, my - 18, 36, 36))
        if i == 2:
            zones.append((mx - 374, my - 28, 352, 58))
        else:
            zones.append((mx + 20, my - 28, 392, 58))
    placed, attempts = 0, 0
    while placed < 30 and attempts < 500:
        attempts += 1
        x, y = rng.uniform(26, 854), rng.uniform(66, 426)
        if any(zx <= x <= zx + zw and zy <= y <= zy + zh for zx, zy, zw, zh in zones):
            continue
        h = rng.uniform(9, 22)
        col = t["tree1"] if rng.random() < 0.6 else t["tree2"]
        s += pines_g(x, y, h, h * 0.42, col, tiers=2)
        placed += 1

    if t["ff"]:
        n = 0
        while n < 5:
            x, y = rng.uniform(40, 840), rng.uniform(70, 420)
            if any(zx <= x <= zx + zw and zy <= y <= zy + zh for zx, zy, zw, zh in zones):
                continue
            d, dd = rng.uniform(3.5, 6.5), rng.uniform(0, 4)
            s += (f'<circle class="ffp" style="--p:{d:.1f}s;--dd:{dd:.1f}s" cx="{x:.1f}" cy="{y:.1f}" '
                  f'r="1.6" fill="{FIREFLY}"/>')
            n += 1
    else:
        for bx, by, sc in ((548, 84, 0.9), (596, 70, 0.7)):
            s += (f'<path d="M{bx},{by} q{5.6 * sc:.1f},{-4.8 * sc:.1f} {11.2 * sc:.1f},0 '
                  f'q{5.6 * sc:.1f},{-4.8 * sc:.1f} {11.2 * sc:.1f},0" stroke="{STEM}" '
                  f'stroke-width="{1.4 * sc:.1f}" fill="none" stroke-linecap="round" opacity=".6"/>')

    for i, ((name, desc, lang), (mx, my)) in enumerate(zip(WAYPOINTS, MARKS)):
        stars = DATA["stars"].get(name, 0)
        s += (f'<circle cx="{mx}" cy="{my}" r="11" fill="{t["panel"]}" stroke="{t["gold"]}" stroke-width="1.5"/>'
              + pines_g(mx, my + 6.5, 11, 4, t["icon"], tiers=2))
        if i == 2:
            tx, anch = mx - 26, ' text-anchor="end"'
        else:
            tx, anch = mx + 26, ""
        s += (f'<text x="{tx}" y="{my - 15}" font-size="9" letter-spacing="1.5" fill="{t["faint"]}"{anch}>'
              f"WP 0{i + 1} · {lang.upper()}</text>"
              f'<text x="{tx}" y="{my + 2}" font-size="15" font-weight="700" fill="{t["ink"]}"{anch}>{name}</text>'
              f'<text x="{tx}" y="{my + 19}" font-size="11.5" fill="{t["dim"]}"{anch}>{desc}</text>')
        s += (f'<path transform="translate(812,{my - 4}) scale(.8)" d="{STAR_PATH}" fill="{t["gold"]}"/>'
              f'<text x="826" y="{my + 1}" font-size="12.5" fill="{t["ink"]}">{stars}</text>')

    s += (f'<text x="30" y="40" font-size="12" letter-spacing="2.5" fill="{t["ink"]}">'
          "TRAIL MAP · FEATURED PROJECTS</text>")
    s += (f'<circle cx="820" cy="33" r="16" fill="none" stroke="{t["dim"]}" stroke-width="1.2"/>'
          f'<polygon points="816,33 820,21 824,33" fill="{t["gold"]}"/>'
          f'<polygon points="816,33 820,45 824,33" fill="{t["dim"]}" opacity=".6"/>'
          f'<text x="820" y="15" font-size="8" text-anchor="middle" fill="{t["faint"]}">N</text>')
    ly = 461
    s += (f'<line x1="30" y1="{ly - 4}" x2="66" y2="{ly - 4}" stroke="{t["trail"]}" stroke-width="2.5" '
          'stroke-dasharray="1 7" stroke-linecap="round"/>'
          f'<text x="74" y="{ly}" font-size="10" fill="{t["faint"]}">trail</text>'
          f'<path transform="translate(130,{ly - 8}) scale(.6)" d="{STAR_PATH}" fill="{t["gold"]}"/>'
          f'<text x="141" y="{ly}" font-size="10" fill="{t["faint"]}">stars</text>'
          + pines_g(200, ly + 2, 10, 4, t["tree2"], tiers=2)
          + f'<text x="210" y="{ly}" font-size="10" fill="{t["faint"]}">forest</text>'
          f'<text x="848" y="{ly}" font-size="10" text-anchor="end" fill="{t["faint"]}">'
          "4 marked routes · updated nightly</text>")
    return s


def trail_slices(t):
    scene = trail_scene(t)
    parts = [("head", 0, 64, "Trail map", "Featured projects as waypoints on a forest trail map."),
             ("legend", 432, 48, "Trail map legend", "Dashed line: trail. Star: stars. Pines: forest.")]
    for i, (name, desc, _lang) in enumerate(WAYPOINTS):
        parts.insert(1 + i, (f"wp{i + 1}", 64 + 92 * i, 92, name,
                             f"{name}: {desc} {DATA['stars'].get(name, 0)} stars."))
    for part, y0, h, ti, de in parts:
        body = (f'<svg xmlns="http://www.w3.org/2000/svg" width="880" height="{h}" '
                f'viewBox="0 {y0} 880 {h}" role="img" aria-labelledby="t d">'
                f"<title id=\"t\">{ti}</title><desc id=\"d\">{de}</desc>"
                f"<style>{COMMON_CSS}</style>{scene}</svg>")
        (OUT / f"trail-{part}{t['sfx']}.svg").write_text(body)


def contribution_forest(t):
    rng = random.Random(11)
    W, H = 880, 196
    base_y = 150
    vals = DATA["calendar"]
    maxv, total = max(vals), DATA["cal_total"]

    s = svg_open(W, H, "Contribution forest",
                 f"One pine per day over the last year; {total} contributions.")
    s += f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="10" fill="{t["panel"]}" stroke="{t["pline"]}" stroke-width="1.5"/>'
    s += (f'<text x="34" y="27" font-size="10" letter-spacing="2" fill="{t["faint"]}">'
          "CONTRIBUTION FOREST · LAST 12 MONTHS</text>")
    s += (f'<radialGradient id="g_m"><stop offset="0" stop-color="{t["gold"] if t["light"] else "#CFE7D0"}" stop-opacity=".7"/>'
          f'<stop offset="1" stop-color="{t["gold"] if t["light"] else "#CFE7D0"}" stop-opacity="0"/></radialGradient>'
          f'<circle cx="822" cy="30" r="24" fill="url(#g_m)" opacity=".35"/>'
          f'<circle cx="822" cy="30" r="9" fill="{"#F0D98F" if t["light"] else "#E9F3E3"}"/>')
    if t["star"]:
        for _ in range(12):
            s += (f'<circle cx="{rng.uniform(420, 790):.0f}" cy="{rng.uniform(14, 44):.0f}" '
                  f'r="{rng.uniform(0.5, 1.0):.1f}" fill="{t["star"]}" opacity="{rng.uniform(.2, .55):.2f}"/>')

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
    for v, x, ty in sorted(tops, reverse=True)[:4]:
        if t["ff"]:
            d = rng.uniform(3.5, 6)
            s += (f'<circle class="ffp" style="--p:{d:.1f}s;--dd:{rng.uniform(0, 3):.1f}s" '
                  f'cx="{x:.1f}" cy="{ty - 6:.1f}" r="1.5" fill="{FIREFLY}"/>')
        else:
            s += f'<circle cx="{x:.1f}" cy="{ty - 6:.1f}" r="1.5" fill="{t["gold"]}" opacity=".7"/>'

    s += (f'<text x="34" y="178" font-size="10.5" fill="{t["faint"]}">$ git log --since=&quot;1 year ago&quot; '
          f'--oneline | wc -l&#160;&#160;→&#160;&#160;{total:,} contributions</text>')
    s += f'<text x="742" y="178" font-size="10" text-anchor="end" fill="{t["faint"]}">less</text>'
    for k, lx in enumerate((752, 764, 776, 788)):
        tt = (0.12, 0.4, 0.7, 1.0)[k]
        s += pines_g(lx, 181, 5 + k * 3.2, 4 + k * 0.8, lerp_hex(t["lerp0"], t["lerp1"], tt), tiers=2)
    s += f'<text x="798" y="178" font-size="10" fill="{t["faint"]}">more</text>'
    (OUT / f"contribution-forest{t['sfx']}.svg").write_text(s + "</svg>")


def lang_rings(t):
    W, H = 880, 200
    langs = DATA["langs"]
    total = sum(langs.values())
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    rows = [(k, v / total) for k, v in top]
    rows.append(("other", (total - sum(v for _, v in top)) / total))

    s = svg_open(W, H, "Language rings",
                 "Language share across all public repos, by bytes of source.")
    s += f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="10" fill="{t["panel"]}" stroke="{t["pline"]}" stroke-width="1.5"/>'
    s += (f'<text x="34" y="27" font-size="10" letter-spacing="2" fill="{t["faint"]}">'
          "LANGUAGE RINGS · ALL PUBLIC REPOS</text>")
    cx, cy = 150, 116
    s += f'<circle cx="{cx}" cy="{cy}" r="62" fill="{WOOD}"/>'
    for k, r in enumerate(range(54, 10, -7)):
        s += (f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{r * 0.96:.1f}" fill="none" '
              f'stroke="{RING}" stroke-width="1.2" opacity=".55" '
              f'transform="rotate({k * 9} {cx} {cy})"/>')
    s += (f'<circle cx="{cx}" cy="{cy}" r="62" fill="none" stroke="{BARK}" stroke-width="5"/>'
          f'<path d="M{cx},{cy} L{cx + 40},{cy - 26}" stroke="{CRACK}" stroke-width="1.5" opacity=".7"/>'
          f'<path d="M{cx},{cy} L{cx - 16},{cy + 44}" stroke="{CRACK}" stroke-width="1.5" opacity=".7"/>'
          f'<text x="{cx}" y="196" font-size="9.5" text-anchor="middle" fill="{t["faint"]}">'
          f"{total / 1e6:.1f} MB of source</text>")
    for k, (name, share) in enumerate(rows):
        y = 62 + k * 22
        color = LANG_COLORS.get(name, OTHER_COLOR)
        s += (f'<text x="300" y="{y}" font-size="11.5" fill="{t["ink"]}">{name}</text>'
              f'<rect x="398" y="{y - 7}" width="370" height="8" rx="2" fill="{t["ink"]}" opacity=".08"/>'
              f'<rect x="398" y="{y - 7}" width="{max(3, 370 * share):.1f}" height="8" rx="2" fill="{color}"/>'
              f'<text x="846" y="{y}" font-size="11" text-anchor="end" fill="{t["dim"]}">{share * 100:.1f}%</text>')
    (OUT / f"lang-rings{t['sfx']}.svg").write_text(s + "</svg>")


def campfire(t):
    W, H = 880, 120
    s = svg_open(W, H, "Campfire",
                 "A campsite footer. At night the fire burns; by day, smoke and birds.")
    s += f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="10" fill="{t["panel"]}" stroke="{t["pline"]}" stroke-width="1.5"/>'
    s += f'<rect x="24" y="94" width="832" height="1.5" fill="{t["ground"]}"/>'
    s += (f'<polygon points="112,94 150,48 188,94" fill="{t["inset"]}" stroke="{t["iline"]}" stroke-width="1.5"/>'
          f'<line x1="150" y1="48" x2="150" y2="94" stroke="{t["iline"]}" stroke-width="1.2"/>'
          f'<polyline points="140,94 150,72 160,94" fill="none" stroke="{t["iline"]}" stroke-width="1.2"/>')
    s += (pines_g(468, 94, 24, 8.5, t["tree1"]) + pines_g(498, 94, 16, 6, t["tree2"], tiers=2)
          + pines_g(640, 94, 20, 7, t["tree1"], tiers=2))
    s += (f'<rect x="-14" y="-2.5" width="28" height="5" rx="2" transform="translate(250,92) rotate(18)" fill="{CRACK}"/>'
          f'<rect x="-14" y="-2.5" width="28" height="5" rx="2" transform="translate(250,92) rotate(-18)" fill="{CRACK}"/>')
    if t["ff"]:
        s += ('<radialGradient id="g_fire"><stop offset="0" stop-color="#FFD36E" stop-opacity=".55"/>'
              '<stop offset="1" stop-color="#FFD36E" stop-opacity="0"/></radialGradient>'
              '<circle cx="250" cy="76" r="36" fill="url(#g_fire)"/>')
        s += ('<g transform="translate(250,89)">'
              '<path class="fl" style="--fd:.95s" d="M0,0 C-9,-9 -7,-21 0,-30 C7,-21 9,-9 0,0" fill="#D9A441"/>'
              '<path class="fl" style="--fd:1.25s" d="M0,0 C-6,-6 -4.8,-14 0,-20 C4.8,-14 6,-6 0,0" fill="#FFD36E"/>'
              '<path class="fl" style="--fd:.8s" d="M0,0 C-3.5,-4 -2.8,-8.5 0,-12 C2.8,-8.5 3.5,-4 0,0" fill="#FFF2C9"/>'
              "</g>")
        for sx, d, dd in ((243, 2.4, 0.3), (250, 3.1, 1.2), (257, 2.7, 0.7), (247, 3.5, 2.0)):
            s += (f'<circle class="spk" style="--d:{d}s;--dd:{dd}s" cx="{sx}" cy="62" r="1.2" '
                  f'fill="{FIREFLY}"/>')
        line1, line2 = "connection closed", "the forest sleeps · regenerated nightly by forest.yml"
    else:
        s += (f'<path class="smoke" d="M250,86 C242,70 260,58 252,42 C246,30 254,22 250,10" '
              f'fill="none" stroke="{t["dim"]}" stroke-width="2" stroke-linecap="round" opacity=".4"/>')
        for bx, by, sc in ((560, 40, 0.9), (604, 28, 0.7)):
            s += (f'<path d="M{bx},{by} q{5.6 * sc:.1f},{-4.8 * sc:.1f} {11.2 * sc:.1f},0 '
                  f'q{5.6 * sc:.1f},{-4.8 * sc:.1f} {11.2 * sc:.1f},0" stroke="{STEM}" '
                  f'stroke-width="{1.4 * sc:.1f}" fill="none" stroke-linecap="round" opacity=".6"/>')
        line1, line2 = "gone hiking — back at dusk", "regenerated nightly by forest.yml"
    s += (f'<text x="846" y="54" font-size="13.5" text-anchor="end" fill="{t["ink"]}">{line1}</text>'
          f'<text x="846" y="76" font-size="10.5" text-anchor="end" fill="{t["faint"]}">{line2}</text>')
    (OUT / f"campfire{t['sfx']}.svg").write_text(s + "</svg>")


# ---------------------------------------------------------------- data
def gh_json(url, tok, payload=None):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "forest-profile"})
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
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
    except Exception as e:
        print("languages fetch failed, keeping old:", e)
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
    data["fetched"] = datetime.date.today().isoformat()
    path.write_text(json.dumps(data))
    print("data.json refreshed", data["fetched"])


if __name__ == "__main__":
    if "--fetch" in sys.argv:
        fetch_live()
        sys.exit(0)
    OUT = HERE
    if "--out" in sys.argv:
        OUT = pathlib.Path(sys.argv[sys.argv.index("--out") + 1])
    OUT.mkdir(parents=True, exist_ok=True)
    DATA = json.loads((HERE / "data.json").read_text())

    header(NIGHT, "header-dark.svg")
    header(DAY, "header-light.svg")
    for t in (T_DARK, T_LIGHT):
        button(t, "link-site", "pine", "luizperren.dev")
        button(t, "link-youtube", "play", "YouTube")
        button(t, "link-sponsor", "heart", "Sponsor", grey=True)
        button(t, "link-contact", "mail", "Contact")
        trail_slices(t)
        contribution_forest(t)
        lang_rings(t)
        campfire(t)
    print("rendered:", len(list(OUT.glob("*.svg"))), "SVGs in", OUT)
