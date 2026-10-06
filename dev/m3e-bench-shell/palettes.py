#!/usr/bin/env python3
"""Palettes of the Shell bench: dark and light renders of the theme, plus the SystemUI roles of the colour sheet.

render_theme.render() (dev/m3e-bench) renders the theme templates with the fixed seed (fallback_color of
theme/matugen/palette.json) into <out>/<mode>/. The GTK colour sheet it writes (colors-gtk4.css) only holds the
roles of the base theme's template; the expected rows also use the SystemUI roles surface_effect_0..3 (docs/design-notes.md), which
live in palette.json: their colour and their opacity (and "@overview_ink", the content colour on the
overview background, which depends on the mode) are appended to <out>/<mode>/colors.css, the sheet that
measure.py reads ("@surface_effect_N" = opaque colour; "--surface_effect_N-opacity" = the role's own opacity, the
"@role" opacity of an expected tuple).

Usage: palettes.py --out DIR [--seed #rrggbb] [--base-theme DIR] [--theme-root DIR]
Writes DIR/{dark,light}/{gnome-shell.css, shell/, colors.css, palette.json, ...}.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "m3e-bench"))
import render_theme  # noqa: E402

MODES = ("dark", "light")
EFFECT_ROLE = re.compile(r"surface_effect_\d+")


def effect_lines(palette):
    """CSS custom properties (colour and opacity) of the surface_effect_N roles of a palette.json dict."""
    colors = palette["colors"]
    return "".join(f"  --{name}: {colors[name]['default']['hex']};\n"
                   f"  --{name}-opacity: {colors[name]['default']['opacity']};\n"
                   for name in sorted(colors) if EFFECT_ROLE.fullmatch(name))


def overview_lines(palette, mode):
    """CSS custom property `--overview_ink`: the content colour on the overview background (#overviewGroup).
    The dark overview is a surface (on_surface content); the light one is primary (on_primary content, see the
    light-overview part of the Shell sheet)."""
    role = "on_surface" if mode == "dark" else "on_primary"
    return f"  --overview_ink: {palette['colors'][role]['default']['hex']};\n"


def write_colors(mode_dir):
    """<mode_dir>/colors.css = colors-gtk4.css + the surface_effect_N roles and the overview ink of <mode_dir>/palette.json."""
    mode_dir = Path(mode_dir)
    palette = json.loads((mode_dir / "palette.json").read_text(encoding="utf-8"))
    base = (mode_dir / "colors-gtk4.css").read_text(encoding="utf-8")
    lines = effect_lines(palette)
    if lines:
        lines += overview_lines(palette, mode_dir.name)
    if not lines:
        raise ValueError(f"{mode_dir / 'palette.json'}: no surface_effect_N role (is this the m3e-gnome palette?)")
    out = mode_dir / "colors.css"
    out.write_text(f"{base}\n/* SystemUI roles (palette.json) */\n:root {{\n{lines}}}\n", encoding="utf-8")
    return out


def render_all(out, seed=None, base_theme=None, theme_root=None):
    out = Path(out)
    for mode in MODES:
        mode_dir = render_theme.render(out / mode, mode, seed, base_theme, theme_root)
        write_colors(mode_dir)
    return out


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", required=True)
    p.add_argument("--seed")
    p.add_argument("--base-theme")
    p.add_argument("--theme-root")
    a = p.parse_args(argv)
    try:
        render_all(a.out, a.seed, a.base_theme, a.theme_root)
    except (ValueError, RuntimeError, OSError, KeyError) as e:
        print(f"palettes: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
