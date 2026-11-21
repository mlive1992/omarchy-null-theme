#!/usr/bin/env python3
"""Render the intro for the default wallpaper (01-form-study-clean).

The shapes come out of a blur one by one; the red quarter disc, the one signal,
arrives last. The clip ends by dissolving into the still itself, so Omarchy's
hand-off from video to wallpaper is seamless.

Needs rsvg-convert, ImageMagick and ffmpeg. Run:  python3 tools/make-intro.py
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("art", os.path.join(HERE, "make-art.py"))
art = importlib.util.module_from_spec(spec)
spec.loader.exec_module(art)
# Intros ship at 2560x1440 like Omarchy's own; the art code reads these globals at call time.
art.W, art.H, art.U = 2560, 1440, 0.5

FPS, SECONDS = 24, 6
FRAMES = FPS * SECONDS
NAME = "01-form-study-clean"
STILL = os.path.join(art.BG_DIR, NAME + ".webp")
OUT = os.path.join(art.BG_DIR, "intros", NAME + ".mp4")
PREVIEW = os.path.join(art.ROOT, "previews", f"intro-{NAME}.webp")

# part: (start, end) in seconds of its move from blurred and faint to sharp and solid
TIMELINE = {
    "band": (0.3, 2.0),
    "capsule": (0.8, 2.6),
    "circle": (1.4, 3.2),
    "square": (2.0, 3.8),
    "marks": (3.4, 4.2),
    "signal": (4.0, 4.7),  # last, and quicker: the signal switching on
}
DISSOLVE = (5.1, 5.6)  # into the still; held to the end


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def anim_at(sec):
    def anim(part):
        a, b = TIMELINE[part]
        k = ease((sec - a) / (b - a))
        return k, (1 - k) * 160  # opacity, extra blur in 5120-wide units
    return anim


def frame(args):
    i, tmp = args
    out = os.path.join(tmp, f"f{i:04d}.png")
    sec = i / FPS
    if sec >= DISSOLVE[1]:
        subprocess.run(["cp", os.path.join(tmp, "still.png"), out], check=True)
        return
    svg = art.shapes(True, anim=anim_at(sec))
    art.render(svg, out, 0.6, png=True, bg="#0a0a0a", bg_grain=0.25)
    k = ease((sec - DISSOLVE[0]) / (DISSOLVE[1] - DISSOLVE[0]))
    if k > 0:
        subprocess.run(["magick", out, os.path.join(tmp, "still.png"), "-compose", "Blend",
                        "-define", f"compose:args={k * 100:.1f}", "-composite", out], check=True)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["magick", STILL, "-resize", f"{art.W}x{art.H}!", os.path.join(tmp, "still.png")], check=True)
        with Pool(os.cpu_count()) as pool:
            pool.map(frame, [(i, tmp) for i in range(FRAMES)])
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                        "-i", os.path.join(tmp, "f%04d.png"), "-c:v", "libx264", "-preset", "slow",
                        # fresh grain every frame is costly; this lands near the size of Omarchy's own intros
                        "-tune", "grain", "-crf", "25", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
                       check=True)
        # small looping preview for the README
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", OUT, "-vf", "fps=12,scale=640:-1",
                        "-loop", "0", "-quality", "70", PREVIEW], check=True)
    print("wrote", os.path.relpath(OUT, art.ROOT), "and", os.path.relpath(PREVIEW, art.ROOT))


if __name__ == "__main__":
    sys.exit(main())
