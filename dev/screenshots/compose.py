#!/usr/bin/env python3
"""Turn the raw captures of capture.sh into the optimized files of screenshots/.

Usage: compose.py --raw DIR --out DIR [--palette-raw DIR]
  --raw DIR          capture.sh output of the main run (<DIR>/dark/*.png and <DIR>/light/*.png)
  --palette-raw DIR  directory holding one capture.sh output per wallpaper, named <wallpaper> (dunes, ocean, dusk, forest),
                     each run with --scenarios palette --modes dark; builds palette-from-wallpaper.png
Files are written losslessly (Pillow, optimize); a PNG above LIMIT_KB is reduced to a 256-colour palette with
Floyd-Steinberg dithering (only the dimmed dialog backdrop needs it).
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LIMIT_KB = 400
# dialog: the dialog and the dimmed windows around it (the full dimmed frame is 0.5-0.8 MB and adds nothing)
DIALOG_BOX = (560, 380, 1360, 700)
# final name -> (mode or None, raw capture name, crop box (x0, y0, x1, y1) or None)
SHOTS = {
    "overview-dark": ("dark", "overview", None),
    "overview-light": ("light", "overview", None),
    "quick-settings-dark": ("dark", "quick-settings", None),
    "quick-settings-light": ("light", "quick-settings", None),
    "notifications-dark": ("dark", "notifications", None),
    "calendar-light": ("light", "notifications", None),
    "settings-gtk4-dark": ("dark", "app-settings", None),
    "settings-gtk4-light": ("light", "app-settings", None),
    "files-gtk4-dark": ("dark", "app-files", None),
    "files-gtk4-light": ("light", "app-files", None),
    "terminal-dark": ("dark", "app-terminal", None),
    "terminal-light": ("light", "app-terminal", None),
    "app-grid-dark": ("dark", "app-grid", None),
    "app-grid-light": ("light", "app-grid", None),
    "dialogs-dark": ("dark", "dialog", DIALOG_BOX),
    "dialogs-light": ("light", "dialog", DIALOG_BOX),
    "desktop-dark": ("dark", "desktop", None),
    "desktop-light": ("light", "desktop", None),
    "alt-tab-dark": ("dark", "alt-tab", None),
}
# status bar: top-right corner of the quick settings capture (bar with the Android-style icons and battery pill, panel
# below), shown at 2x so that the icons are legible.
STATUS_BOX = (1380, 0, 1920, 400)
STATUS_SCALE = 2
ROLES = ["primary", "primary_container", "secondary_container", "tertiary_container", "surface",
         "surface_container_high"]


def save(img, path):
    img = img.convert("RGB")
    img.save(path, optimize=True)
    if path.stat().st_size > LIMIT_KB * 1024:
        img.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(path, optimize=True)
    return path.stat().st_size


def hex_to_rgb(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def palette_montage(palette_raw, out, font_path):
    """One column per wallpaper: the wallpaper, the resulting desktop, the eight roles of its palette."""
    names = ["dunes", "ocean", "dusk", "forest"]
    col_w, thumb_w, thumb_h, gap, pad = 400, 380, 214, 20, 30
    label = ImageFont.truetype(str(font_path), 22)
    small = ImageFont.truetype(str(font_path), 15)
    width = pad * 2 + col_w * len(names) - (col_w - thumb_w)
    height = pad * 2 + 40 + (thumb_h + gap) * 2 + 56 + 40
    canvas = Image.new("RGB", (width, height), (24, 20, 18))
    draw = ImageDraw.Draw(canvas)
    for i, name in enumerate(names):
        raw = Path(palette_raw) / name / "dark"
        x, y = pad + i * col_w, pad
        draw.text((x, y), name.capitalize(), font=label, fill=(238, 224, 218))
        y += 40
        canvas.paste(Image.open(raw / "wallpaper.png").convert("RGB").resize((thumb_w, thumb_h), Image.LANCZOS), (x, y))
        y += thumb_h + gap
        canvas.paste(Image.open(raw / "palette.png").convert("RGB").resize((thumb_w, thumb_h), Image.LANCZOS), (x, y))
        y += thumb_h + gap
        colors = json.loads((raw / "palette" / "palette.json").read_text(encoding="utf-8"))["colors"]
        cell = thumb_w // len(ROLES)
        for j, role in enumerate(ROLES):
            rgb = hex_to_rgb(colors[role]["default"]["hex"])
            draw.rounded_rectangle((x + j * cell, y, x + (j + 1) * cell - 4, y + 56), radius=10, fill=rgb)
        for text, first, last in (("primary", 0, 0), ("containers", 1, 3), ("surfaces", 4, 5)):
            middle = x + (first + last + 1) * cell / 2
            draw.text((middle, y + 66), text, font=small, fill=(180, 168, 162), anchor="ma")
    return save(canvas, out / "palette-from-wallpaper.png")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--raw", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--palette-raw")
    a = p.parse_args()
    raw, out = Path(a.raw), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, (mode, capture, box) in SHOTS.items():
        source = raw / mode / f"{capture}.png"
        if not source.is_file():
            print(f"missing {source}")
            continue
        img = Image.open(source)
        print(f"{name}.png {save(img.crop(box) if box else img, out / f'{name}.png') // 1024} KB")
    for mode in ("dark", "light"):
        source = raw / mode / "quick-settings.png"
        if source.is_file():
            img = Image.open(source).convert("RGB").crop(STATUS_BOX)
            img = img.resize((img.width * STATUS_SCALE, img.height * STATUS_SCALE), Image.LANCZOS)
            print(f"status-bar-{mode}.png {save(img, out / f'status-bar-{mode}.png') // 1024} KB")
    if a.palette_raw:
        font = next(Path(a.palette_raw).glob("*/dark/stage/fonts/GoogleSansFlex/*.ttf"))
        print(f"palette-from-wallpaper.png {palette_montage(a.palette_raw, out, font) // 1024} KB")


if __name__ == "__main__":
    main()
