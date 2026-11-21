#!/usr/bin/env python3
"""Generate Null's wallpapers and dot-matrix unlock logo.

Stdlib only; needs rsvg-convert and ImageMagick (magick) on PATH.
Run from anywhere:  python3 tools/make-art.py [--fast]
--fast renders at 1/4 size for quick previews.
"""
import math
import os
import random
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BG_DIR = os.path.join(ROOT, "backgrounds")
FAST = "--fast" in sys.argv
W, H = (1280, 720) if FAST else (5120, 2880)
U = W / 5120  # unit: 1 at full size
BLEED = int(400 * U)  # extra margin for art whose blurs reach the frame edge

RED = "#d71921"
FONT = "JetBrains Mono, monospace"


def svg(body, bg, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f"<defs>{defs}</defs><rect width='100%' height='100%' fill='{bg}'/>{body}</svg>")


def blur(id_, sd):
    return (f'<filter id="{id_}" x="-100%" y="-200%" width="300%" height="500%">'
            f'<feGaussianBlur stdDeviation="{sd * U:.1f}"/></filter>')


def cross(x, y, size, color, op=0.6):
    s, w = size * U, max(1, 2 * U)
    return (f'<g stroke="{color}" stroke-width="{w:.1f}" opacity="{op}">'
            f'<line x1="{x - s:.1f}" y1="{y:.1f}" x2="{x + s:.1f}" y2="{y:.1f}"/>'
            f'<line x1="{x:.1f}" y1="{y - s:.1f}" x2="{x:.1f}" y2="{y + s:.1f}"/></g>')


def corner_marks(color):
    m = 140 * U
    return "".join(cross(x, y, 18, color, 0.35) for x in (m, W - m) for y in (m, H - m))


# --- 01/02: blurred, grainy shapes in a horizontal row, dark and light ------------------
def shapes(dark, anim=None):
    """Shapes only, on a transparent canvas: render() grains them, then lays them on the background.

    anim: optional fn(part) -> (opacity, extra blur) for the intro; parts are
    band, capsule, circle, signal, square, marks. Without it this is the still.
    """
    ink = ("#3a3a3a", "#5c5c5c", "#7d7d7d") if dark else ("#2b2b2b", "#555555", "#8a8a8a")
    line = "#e6e6e6" if dark else "#1a1a1a"
    cy = H * 0.5
    defs = blur("b1", 40) + blur("b2", 90) + blur("b3", 14)
    defs += (f'<linearGradient id="lg" x1="0" y1="0" x2="1" y2="0">'
             f'<stop offset="0" stop-color="{ink[2]}"/><stop offset="1" stop-color="{ink[0]}"/></linearGradient>'
             f'<linearGradient id="lv" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="{ink[1]}"/>'
             + f'<stop offset="1" stop-color="{ink[1]}" stop-opacity="0"/>'
             + '</linearGradient>')
    b = []

    def put(part, el):
        nonlocal defs
        if anim is None:
            b.append(el)
            return
        op, sd = anim(part)
        if op <= 0.002:
            return
        filt = ""
        if sd > 0.5:
            defs += blur(f"a_{part}", sd)
            filt = f' filter="url(#a_{part})"'
        b.append(f'<g opacity="{op:.3f}"{filt}>{el}</g>')

    # wide fog band behind everything on the left
    put("band", f'<rect x="{560 * U:.1f}" y="{cy - 120 * U:.1f}" width="{900 * U:.1f}" height="{240 * U:.1f}" '
                f'fill="{ink[1]}" opacity="0.7" filter="url(#b2)"/>')
    # horizontal capsule, soft
    put("capsule", f'<rect x="{1180 * U:.1f}" y="{cy - 300 * U:.1f}" width="{1050 * U:.1f}" height="{600 * U:.1f}" '
                   f'rx="{300 * U:.1f}" fill="url(#lg)" filter="url(#b3)"/>')
    # sharp circle overlapping the capsule's end
    put("circle", f'<circle cx="{2380 * U:.1f}" cy="{cy:.1f}" r="{330 * U:.1f}" fill="{ink[0]}"/>')
    # red quarter disc, the one signal
    qx, qy, qr = 2760 * U, cy + 330 * U, 330 * U
    put("signal", f'<path d="M{qx:.1f},{qy:.1f} L{qx:.1f},{qy - qr:.1f} A{qr:.1f},{qr:.1f} 0 0 1 {qx + qr:.1f},{qy:.1f} Z" fill="{RED}"/>')
    # square dissolving into a fog
    put("square", f'<rect x="{3200 * U:.1f}" y="{cy - 330 * U:.1f}" width="{660 * U:.1f}" height="{660 * U:.1f}" '
                  f'rx="{36 * U:.1f}" fill="url(#lv)" filter="url(#b1)"/>')
    put("marks", "".join(cross(x * U, cy, 46, line, 0.5) for x in (1500, 2380, 2760, 3530)) + corner_marks(line))
    return svg("".join(b), "none", defs)


# --- 03: a grooved disc out of focus, with a patch of red light -----------------------------
def groove():
    # Palette sampled from the reference photo.
    P = dict(sky="#A0B5B6", far="#A4B9BA", mid="#708C8D", floor="#1D3833",
             dark_l="#2B3E37", dark_tr="#253A35", dark_ll="#3C4A43",
             body="#4D6263", body_hi="#5A7373", body_dk="#2D423D", wedge="#97B9B6", rim="#79A1A1",
             red_top="#CD8A7F", red="#DB7C6A", red_edge="#AB5C4E",
             swell="#89ACA8", teal="#4B7B80", dark_br="#435755")

    def c(x, y, r, extra):
        return f'<circle cx="{x * U:.1f}" cy="{y * U:.1f}" r="{r * U:.1f}" {extra}/>'

    soft = []

    def blob(x, y, rx, ry, colour, op):
        gid = f"soft{len(soft)}"
        soft.append(f'<radialGradient id="{gid}"><stop offset="0" stop-color="{colour}" stop-opacity="{op}"/>'
                    f'<stop offset="0.55" stop-color="{colour}" stop-opacity="{op * 0.75:.2f}"/>'
                    f'<stop offset="1" stop-color="{colour}" stop-opacity="0"/></radialGradient>')
        return (f'<ellipse cx="{x * U:.1f}" cy="{y * U:.1f}" rx="{rx * U:.1f}" ry="{ry * U:.1f}" '
                f'fill="url(#{gid})"/>')

    ax, ay, ar = 3400, 650, 1550   # far disc, top right, soft ripples
    bx, by, br = 2900, 4000, 2550  # near disc, rising from the bottom
    top = by - br
    defs = blur("g1", 4) + blur("g2", 18) + blur("g3", 45) + blur("g5", 9)
    defs += (f'<linearGradient id="sky" x1="0" y1="0" x2="0.25" y2="1">'
             f'<stop offset="0" stop-color="{P["sky"]}"/><stop offset="0.6" stop-color="{P["mid"]}"/>'
             f'<stop offset="1" stop-color="{P["floor"]}"/></linearGradient>'
             f'<radialGradient id="farDisc" gradientUnits="userSpaceOnUse" cx="{ax * U:.1f}" cy="{ay * U:.1f}" r="{ar * U:.1f}">'
             f'<stop offset="0" stop-color="{P["far"]}"/><stop offset="1" stop-color="{P["sky"]}"/></radialGradient>'
             f'<linearGradient id="nearDisc" gradientUnits="userSpaceOnUse" x1="0" y1="{top * U:.1f}" x2="0" y2="{(top + 1500) * U:.1f}">'
             f'<stop offset="0" stop-color="{P["body_hi"]}"/><stop offset="1" stop-color="{P["body"]}"/></linearGradient>'
             f'<clipPath id="near">{c(bx, by, br, "")}</clipPath>')
    b = []
    # dark masses, far out of focus: left edge and top-right corner
    b.append(blob(0, 1650, 1550, 1750, P["dark_l"], 1.0))
    b.append(blob(150, 2900, 1300, 700, P["dark_ll"], 0.8))
    b.append(blob(5250, -150, 1400, 950, P["dark_tr"], 1.0))
    # far disc: a lighter face with blurred concentric ripples
    b.append(f'<g filter="url(#g3)">{c(ax, ay, ar, chr(32) + "fill=" + chr(34) + "url(#farDisc)" + chr(34))}</g>')
    b.append(f'<g fill="none" stroke="{P["mid"]}" stroke-width="{10 * U:.1f}" opacity="0.32" filter="url(#g5)">'
             # ripples fade in from the centre so it never reads as a bullseye
             + "".join(c(ax, ay, r, f'stroke-opacity="{min(1, (r - 120) / 900):.2f}"') for r in range(156, ar, 36)) + "</g>")
    # near disc, clipped so nothing spills past its rim
    near = [c(bx, by, br, 'fill="url(#nearDisc)"')]
    # red light: a slice of the rim band, so its edges run with the grooves like in the photo
    a0, a1 = math.atan2(-2050, 1480 - bx), math.atan2(-2480, 2200 - bx)
    r_out, r_in = br - 60, br - 490

    def arc_pt(r, a):
        return f"{(bx + r * math.cos(a)) * U:.1f},{(by + r * math.sin(a)) * U:.1f}"
    patch = (f'M{arc_pt(r_out, a0)} A{r_out * U:.1f},{r_out * U:.1f} 0 0 1 {arc_pt(r_out, a1)} '
             f'L{arc_pt(r_in, a1 + 0.02)} A{r_in * U:.1f},{r_in * U:.1f} 0 0 0 {arc_pt(r_in, a0 + 0.05)} Z')
    cx_, cy_ = bx + (br - 220) * math.cos((a0 + a1) / 2 + 0.05), by + (br - 220) * math.sin((a0 + a1) / 2 + 0.05)
    defs += (f'<radialGradient id="redLight" gradientUnits="userSpaceOnUse" cx="{cx_ * U:.1f}" cy="{cy_ * U:.1f}" r="{520 * U:.1f}">'
             f'<stop offset="0" stop-color="{P["red"]}"/><stop offset="0.6" stop-color="{P["red"]}"/>'
             f'<stop offset="1" stop-color="{P["red_edge"]}"/></radialGradient>'
             + blur("g6", 26))
    near.append(f'<path d="{patch}" fill="url(#redLight)" filter="url(#g6)"/>')
    near.append(f'<path d="M{arc_pt(r_out, a0 + 0.04)} A{r_out * U:.1f},{r_out * U:.1f} 0 0 1 {arc_pt(r_out, a1)} '
                f'L{arc_pt(r_out - 110, a1)} A{(r_out - 110) * U:.1f},{(r_out - 110) * U:.1f} 0 0 0 {arc_pt(r_out - 110, a0 + 0.06)} Z" '
                f'fill="{P["red_top"]}" opacity="0.7" filter="url(#g2)"/>')
    # each groove: a lit crest and a shaded trough, softened into ridges
    for colour, op, shift in ((P["wedge"], 0.35, 0), (P["body_dk"], 0.45, 13)):
        near.append(f'<g fill="none" stroke="{colour}" stroke-width="{8 * U:.1f}" opacity="{op}" filter="url(#g1)">'
                    + "".join(c(bx, by, r - shift, "") for r in range(br - 40, br - 1400, -26)) + "</g>")
    # a wedge of light crossing the disc diagonally, and deep shade to its left
    near.append(f'<polygon points="{5300 * U:.1f},{1350 * U:.1f} {5300 * U:.1f},{2150 * U:.1f} '
                f'{2300 * U:.1f},{2950 * U:.1f} {2700 * U:.1f},{2250 * U:.1f}" fill="{P["wedge"]}" opacity="0.55" filter="url(#g3)"/>')
    near.append(f'<polygon points="{0:.1f},{2300 * U:.1f} {2500 * U:.1f},{2050 * U:.1f} {2300 * U:.1f},{2950 * U:.1f} {0:.1f},{3300 * U:.1f}" '
                f'fill="{P["body_dk"]}" opacity="0.8" filter="url(#g3)"/>')
    b.append(f'<g clip-path="url(#near)">{"".join(near)}</g>')
    # the rim catches the light
    b.append(c(bx, by, br, f'fill="none" stroke="{P["rim"]}" stroke-width="{12 * U:.1f}" opacity="0.9" filter="url(#g1)"'))
    # foreground: a pale swell, a teal band under it, and a dark floor
    b.append(blob(2300, 3100, 3300, 650, P["swell"], 0.85))
    b.append(blob(2400, 3420, 3400, 380, P["teal"], 0.8))
    b.append(blob(800, 3200, 2400, 600, P["floor"], 0.95))
    b.append(blob(5000, 3100, 1200, 700, P["dark_br"], 0.8))
    return svg("".join(b), "url(#sky)", defs + "".join(soft))


# --- 04: an X-ray of a branch: translucent round leaves on near-black stems -------------------
def branch():
    # Palette sampled from the reference photo. Leaf opacity is picked so overlaps land on
    # its tones: one leaf ~#595A5E, two ~#3C3D3F, three ~#2F3032.
    P = dict(gap="#A2A6A9", gap_lo="#919598", leaf="#1C1D1F", stem="#020203")
    rnd = random.Random(8)
    defs = [f'<linearGradient id="gap" x1="1" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{P["gap"]}"/><stop offset="1" stop-color="{P["gap_lo"]}"/></linearGradient>']
    LEVELS = (3, 5, 9, 14, 24, 36)  # depth-of-field steps for stems
    for sd in sorted(set(LEVELS + (70, 140))):
        defs.append(blur(f"e{sd}", sd))
    defs.append(blur("halo", 18))
    leaves, stems = [], []
    w = lambda v: f"{v * U:.1f}"

    def qpt(p0, p1, p2, t):
        return tuple((1 - t) ** 2 * a + 2 * (1 - t) * t * b + t * t * c for a, b, c in zip(p0, p1, p2))

    def qdir(p0, p1, p2, t):
        dx = 2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0])
        dy = 2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1])
        return math.atan2(dy, dx)

    def leaf(x, y, r, soft=None, op=0.52):
        # flat translucent body (gradients band at this depth) plus a blurred darker core
        sd = soft if soft is not None else rnd.choice((5, 5, 5, 14, 36))
        rot = rnd.uniform(0, 180)
        ry = r * rnd.uniform(0.86, 0.97)
        tf = f'transform="rotate({rot:.0f} {w(x)} {w(y)})"'
        leaves.append(f'<ellipse cx="{w(x)}" cy="{w(y)}" rx="{w(r)}" ry="{w(ry)}" {tf} fill="{P["leaf"]}" '
                      f'opacity="{op:.2f}" filter="url(#e{sd})"/>')
        leaves.append(f'<ellipse cx="{w(x)}" cy="{w(y)}" rx="{w(r * 0.5)}" ry="{w(ry * 0.5)}" {tf} fill="{P["leaf"]}" '
                      f'opacity="{op * 0.45:.2f}" filter="url(#e140)"/>')

    def stem(p0, p1, p2, width, taper=0.45, focus=("sharp",)):
        """A tapered, slightly wandering stem drawn in chunks, each with its own depth of field.

        focus: ("sharp",) | ("soft", sd) leaves the focal plane right after its joint |
               ("soft", sd, True) soft from the start (a twig on a soft branch) | ("tip", t0, sd) blurs from t0 to the tip.
        """
        length = math.dist(p0, p2)
        amp = length * 0.012
        f1, f2 = rnd.uniform(5, 8), rnd.uniform(13, 19)
        ph1, ph2 = rnd.uniform(0, 6.28), rnd.uniform(0, 6.28)
        pts = []
        for i in range(49):
            t = i / 48
            x, y = qpt(p0, p1, p2, t)
            d = qdir(p0, p1, p2, t)
            # natural wander; zero at the base so the stem stays joined to its parent
            o = amp * t * (0.75 * math.sin(f1 * t + ph1) + 0.25 * math.sin(f2 * t + ph2))
            pts.append((x - o * math.sin(d), y + o * math.cos(d)))
        for i in range(0, 48, 3):
            t = i / 48
            seg = pts[i:i + 4]
            d = "M" + " L".join(f"{w(px)},{w(py)}" for px, py in seg)
            sw = width * (1 - taper * t) * (1.3 if i == 0 else 1)  # slight flare at the joint
            if focus[0] == "soft":
                # ramp out of focus over the first chunks, unless already soft where it starts
                steps = [focus[1]] if len(focus) > 2 else [0] + [v for v in LEVELS if v <= focus[1]]
                sd = steps[min(len(steps) - 1, i // 3)]
            elif focus[0] == "tip" and t >= focus[1]:
                sd = LEVELS[min(len(LEVELS) - 1, int((t - focus[1]) / (1 - focus[1]) * len(LEVELS)))]
            else:
                sd = 0
            stems.append((d, sw, sd))
        return pts

    def grow(p0, angle, length, width, depth, focus=("sharp",)):
        bend = rnd.uniform(-0.3, 0.3) * length
        p2 = (p0[0] + length * math.cos(angle), p0[1] + length * math.sin(angle))
        mid = ((p0[0] + p2[0]) / 2, (p0[1] + p2[1]) / 2)
        p1 = (mid[0] - bend * math.sin(angle), mid[1] + bend * math.cos(angle))
        pts = stem(p0, p1, p2, width, focus=focus)
        for t in ((0.5, 0.96) if depth else (0.9,)):
            x, y = pts[round(t * 48)]
            d = qdir(p0, p1, p2, t)
            off = rnd.uniform(0, 90) * rnd.choice((-1, 1))
            # leaves share their stem's depth of field
            soft = focus[1] if focus[0] == "soft" else (36 if focus[0] == "tip" and t > focus[1] + 0.3 else None)
            leaf(x - off * math.sin(d), y + off * math.cos(d), rnd.uniform(620, 860) * (0.8 if depth == 0 else 1), soft=soft)
        if depth:
            t = rnd.uniform(0.25, 0.4)
            x, y = pts[round(t * 48)]
            d = qdir(p0, p1, p2, t)
            twig_focus = ("tip", 0.2, 0) if focus[0] == "tip" else (("soft", focus[1], True) if focus[0] == "soft" else focus)
            grow((x, y), d + rnd.choice((-1, 1)) * rnd.uniform(0.45, 0.8), length * rnd.uniform(0.45, 0.6),
                 width * 0.6, 0, twig_focus)

    # out-of-focus leaves behind everything, spread on a loose grid so no corner sits empty
    for gx in range(4):
        for gy in range(2):
            leaf(gx * 1450 + rnd.uniform(-150, 450), gy * 1700 + rnd.uniform(0, 600), rnd.uniform(850, 1150), soft=70, op=0.38)
    # the trunk rises from the bottom, softening as it leaves the top of the frame, and throws branches both ways
    t0, t1, t2 = (2050, 3000), (2150, 1200), (2900, -150)
    trunk = stem(t0, t1, t2, 22, taper=0.35, focus=("tip", 0.78, 0))
    for t, side in ((0.1, 1), (0.22, -1)):
        x, y = trunk[round(t * 48)]
        leaf(x + side * 520, y - 80, rnd.uniform(650, 800))
    focuses = [("sharp",), ("tip", 0.35, 0), ("soft", 14), ("sharp",), ("soft", 36)]
    for i, t in enumerate((0.2, 0.35, 0.5, 0.64, 0.8)):
        x, y = trunk[round(t * 48)]
        d = qdir(t0, t1, t2, t)
        side = -1 if i % 2 == 0 else 1
        grow((x, y), d + side * rnd.uniform(0.7, 1.05), rnd.uniform(1400, 1900), 13, 1, focuses[i])

    body = "".join(leaves)
    # sharp stems get a dark glow and a crisp core; out-of-focus ones spread into a soft smear
    body += "".join(f'<path d="{d}" fill="none" stroke="{P["leaf"]}" stroke-width="{w(sw * 4)}" stroke-linecap="round" '
                    f'opacity="0.55" filter="url(#halo)"/>' for d, sw, sd in stems if sd < 14)
    for d, sw, sd in stems:
        if sd:
            grow_w = 1 + sd / 30
            body += (f'<path d="{d}" fill="none" stroke="{P["stem"]}" stroke-width="{w(sw * grow_w)}" stroke-linecap="round" '
                     f'stroke-linejoin="round" opacity="{0.9 - sd / 90:.2f}" filter="url(#e{sd})"/>')
        else:
            body += (f'<path d="{d}" fill="none" stroke="{P["stem"]}" stroke-width="{w(sw)}" stroke-linecap="round" '
                     f'stroke-linejoin="round"/>')
    # Render with a bleed margin so blurs at the frame edge see content past it; render() crops it off.
    m = BLEED
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W + 2 * m}" height="{H + 2 * m}">'
            f'<defs>{"".join(defs)}</defs><rect width="100%" height="100%" fill="url(#gap)"/>'
            f'<g transform="translate({m} {m})">{body}</g></svg>')


# --- 05: the Omarchy logo seen through reeded glass ------------------------------------------
def reeded(tmp, dark=False):
    """Raster art (ImageMagick, not SVG): returns a PNG path inside tmp for render(raster_in=...).

    dark: charcoal glass with an off-white logo; the seam highlights carry the ribs instead of the shadows.
    """
    # Light: glass grey from the reference photo (#D8D8D8, faintly cool), taken ~10% darker.
    bg, ink = ("#1C1E1E", "#E6E6E6") if dark else ("#C2C5C5", "#141414")
    rw = 78.7 * U  # rib width: ~65 ribs across, as in the reference
    src = os.path.join(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy"), "themes/catppuccin/unlock.png")
    # Same box as Omarchy's own logo wallpaper: 41.6% of the width, at 29.2% / 41.4% of the frame.
    logo_w, ox, oy = round(W * 0.4164), round(W * 0.2918), round(H * 0.4135)
    cy = oy + logo_w * 188 / 800 / 2  # logo centre line
    flat, glass, dark, light = (os.path.join(tmp, n) for n in ("flat.png", "glass.png", "dark.png", "light.png"))
    subprocess.run(["magick", "-size", f"{W}x{H}", "xc:white",
                    "(", src, "-alpha", "extract", "-negate", "-filter", "point", "-resize", f"{logo_w}x", ")",
                    "-geometry", f"+{ox}+{oy}", "-composite", "-colorspace", "Gray",
                    "-blur", f"0x{max(1, round(2 * U))}", flat], check=True)
    # Gentle refraction: each rib pinches and shifts its slice a little, and stretches it slightly
    # near the seams; the logo stays readable.
    fx = (f"rw={rw:.3f}; rb=floor(i/rw); uu=i/rw-rb;"
          f"xx=i + rw*0.2*sin(2*pi*uu) + rw*0.1*sin(rb*1.3);"
          f"kk=1 - 0.1*exp(-uu*40) - 0.04*exp(-(1-uu)*40);"
          f"yy={cy:.1f} + (j-{cy:.1f})*kk + {10 * U:.1f}*sin(rb*1.7);"
          f"p{{xx,yy}}")
    subprocess.run(["magick", flat, "-virtual-pixel", "White", "-fx", fx, glass], check=True)
    # Seams, measured off the reference: a 1px highlight, a dark line of varying strength,
    # a slight shade after it and a faint second line about a quarter of the way across.
    px = 1 / rw  # one pixel, in rib units
    subprocess.run(["magick", "-size", f"{W}x1", "xc:white", "-fx",
                    f"rw={rw:.3f}; rb=floor(i/rw); uu=i/rw-rb; ss=0.22+0.2*abs(sin(rb*2.3));"
                    f"uu<{px:.4f} ? 1 : uu<{3 * px:.4f} ? 1-ss : uu<0.17 ? 0.985 : (uu>0.27 && uu<0.27+{2 * px:.4f}) ? 0.93 : 1",
                    "-scale", f"{W}x{H}!", dark], check=True)
    subprocess.run(["magick", "-size", f"{W}x1", "xc:black", "-fx",
                    f"rw={rw:.3f}; uu=i/rw-floor(i/rw); uu>1-{px:.4f} || uu<{px:.4f} ? {0.2 if dark else 0.12} : 0",
                    "-scale", f"{W}x{H}!", light], check=True)
    out = os.path.join(tmp, "reeded.png")
    subprocess.run(["magick", glass, "+level-colors", f"{ink},{bg}",
                    dark, "-compose", "Multiply", "-composite",
                    light, "-compose", "Screen", "-composite", out], check=True)
    return out


def render(svg_text, out, grain, png=False, bg=None, bg_grain=0, bleed=False, raster_in=None):
    """bg: the SVG is a transparent layer; grain lands on its shapes only, then it is laid on this colour."""
    with tempfile.TemporaryDirectory() as tmp:
        raster = raster_in  # already-rendered art skips the SVG step
        if raster is None:
            src, raster = os.path.join(tmp, "a.svg"), os.path.join(tmp, "a.png")
            with open(src, "w") as f:
                f.write(svg_text)
            subprocess.run(["rsvg-convert", src, "-o", raster], check=True)
        def grain_layer(amount):
            return ["(", "-size", f"{W // 2}x{H // 2}", "xc:gray50", "-attenuate", str(amount),
                    "+noise", "Gaussian", "-colorspace", "Gray", "-resize", f"{W}x{H}!", ")"]
        noise = grain_layer(grain)
        cmd = ["magick", raster]
        if bleed:
            cmd += ["-crop", f"{W}x{H}+{BLEED}+{BLEED}", "+repage"]
        if bg:
            cmd += ["(", "+clone", "-alpha", "off", *noise, "-compose", "Hard_Light", "-composite", ")",
                    "(", "-clone", "0", "-alpha", "extract", ")", "-delete", "0",
                    "-compose", "CopyOpacity", "-composite", "-compose", "Over", "-background", bg, "-flatten"]
            if bg_grain:  # a lighter second pass over the whole frame
                cmd += [*grain_layer(bg_grain), "-compose", "Hard_Light", "-composite"]
        elif grain:
            # Monochrome film grain at 2px size; hard light keeps it visible on black and white alike.
            cmd += [*noise, "-compose", "Hard_Light", "-composite"]
        cmd += (["-strip", out] if png else ["-quality", "90", "-define", "webp:method=6", out])
        subprocess.run(cmd, check=True)
    print("wrote", os.path.relpath(out, ROOT))


def unlock_logo():
    """Redraw the stock Omarchy unlock logo as a dot matrix."""
    src = os.path.join(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy"), "themes/catppuccin/unlock.png")
    cell = 4
    gw, gh = 800 // cell, 188 // cell
    txt = subprocess.run(["magick", src, "-alpha", "extract", "-filter", "box", "-resize", f"{gw}x{gh}!",
                          "-depth", "8", "txt:-"], check=True, capture_output=True, text=True).stdout
    dots = []
    for ln in txt.splitlines()[1:]:
        pos, rest = ln.split(":", 1)
        x, y = map(int, pos.split(","))
        if int(rest.split("(")[1].split(")")[0].split(",")[0].split(".")[0]) > 140:
            dots.append(f'<circle cx="{x * cell + cell / 2}" cy="{y * cell + cell / 2}" r="{cell * 0.42}"/>')
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="{gh * cell}">'
         f'<g fill="#e6e6e6">{"".join(dots)}</g></svg>')
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "u.svg")
        open(p, "w").write(s)
        subprocess.run(["rsvg-convert", p, "-o", os.path.join(ROOT, "unlock.png")], check=True)
    assert dots, "unlock logo produced no dots"
    print("wrote unlock.png", len(dots), "dots")


if __name__ == "__main__":
    os.makedirs(BG_DIR, exist_ok=True)
    out = lambda name: os.path.join(BG_DIR, name + ".webp")
    render(shapes(True), out("01-form-study-clean"), 0.6, bg="#0a0a0a", bg_grain=0.25)
    render(shapes(False), out("02-form-study-light"), 0.5, bg="#c4c4c4", bg_grain=0.2)
    render(groove(), out("03-groove"), 0.15)
    render(branch(), out("04-branch"), 0.2, bleed=True)
    with tempfile.TemporaryDirectory() as tmp:
        render(None, out("05-reeded"), 0.15, raster_in=reeded(tmp))
        render(None, out("06-reeded-dark"), 0.15, raster_in=reeded(tmp, dark=True))
    if not FAST:
        unlock_logo()
