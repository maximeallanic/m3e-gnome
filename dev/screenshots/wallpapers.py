#!/usr/bin/env python3
"""Procedural demo wallpapers for the README screenshots (CC0: generated here, no third-party artwork).

Usage: wallpapers.py --out DIR [--size 1920x1080]
Writes DIR/{dunes,ocean,dusk,forest}.png: layered, softly shaded ridgelines over a vertical gradient with a blurred
glow. Deterministic (fixed seeds), Pillow only.
"""
import argparse
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

# name -> (sky top, sky bottom, glow, ridge colours back to front, glow position as fraction of the width)
SCENES = {
    "dunes": ((250, 214, 160), (232, 150, 104), (255, 236, 190), [(214, 128, 84), (178, 98, 70), (132, 72, 58), (86, 50, 46)], 0.72),
    "ocean": ((150, 214, 236), (44, 130, 170), (230, 250, 255), [(40, 112, 156), (28, 86, 130), (20, 62, 104), (14, 42, 78)], 0.30),
    "dusk": ((72, 52, 128), (236, 120, 150), (255, 200, 170), [(150, 74, 138), (112, 56, 124), (76, 42, 104), (46, 30, 78)], 0.60),
    "forest": ((196, 228, 170), (96, 170, 120), (255, 252, 214), [(70, 140, 100), (46, 108, 86), (30, 78, 70), (20, 54, 54)], 0.22),
}


# Seed colour of each wallpaper = what `material-palette --image` returns for it (the colour material-sync derives the
# theme from). The quantizer it uses starts from random centroids (dunes once returned the sky colour #f7cc97 out of six
# runs), so the value is pinned here to keep the screenshots reproducible. stage.py --seed-from-image recomputes it.
SEEDS = {"dunes": "#99563c", "ocean": "#5faaca", "dusk": "#5d2e67", "forest": "#92c791"}


def gradient(size, top, bottom):
    w, h = size
    column = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / (h - 1)
        column.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return column.resize(size)


def ridge(size, rng, base, amplitude, colour, shade):
    """One ridgeline polygon, lit from above (vertical fade towards `shade` at the bottom)."""
    w, h = size
    waves = [(rng.uniform(0.6, 2.4), rng.uniform(0, math.tau), rng.uniform(0.25, 1.0)) for _ in range(4)]
    norm = sum(a for _, _, a in waves)
    points = [(x, base + amplitude * sum(a * math.sin(f * math.tau * x / w + p) for f, p, a in waves) / norm)
              for x in range(0, w + 8, 8)]
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon(points + [(w, h), (0, h)], fill=255)
    fill = gradient(size, colour, shade)
    return fill, mask.filter(ImageFilter.GaussianBlur(1.2))


def scene(name, size):
    top, bottom, glow, ridges, glow_x = SCENES[name]
    rng = random.Random(f"m3e-gnome-{name}")
    w, h = size
    img = gradient(size, top, bottom)
    halo = Image.new("RGB", size, (0, 0, 0))
    r = int(h * 0.30)
    ImageDraw.Draw(halo).ellipse((w * glow_x - r, h * 0.30 - r, w * glow_x + r, h * 0.30 + r), fill=glow)
    halo = halo.filter(ImageFilter.GaussianBlur(h * 0.16))
    img = ImageChops.screen(img, halo)
    for i, colour in enumerate(ridges):
        base = h * (0.52 + 0.11 * i)
        fill, mask = ridge(size, rng, base, h * (0.09 - 0.012 * i), colour, tuple(int(c * 0.72) for c in colour))
        img.paste(fill, (0, 0), mask)
    return img


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", required=True)
    p.add_argument("--size", default="1920x1080")
    a = p.parse_args()
    size = tuple(int(v) for v in a.size.split("x"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in SCENES:
        scene(name, size).save(out / f"{name}.png", optimize=True)
        print(out / f"{name}.png")


if __name__ == "__main__":
    main()
