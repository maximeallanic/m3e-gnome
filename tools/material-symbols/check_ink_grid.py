#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools"]
# ///
"""Check the ink grid of the repository icons (theme/icons/Material-Symbols) against the repository stylesheets:
- GTK header bars: application icons, at the size set in m3e-gtk4-buttons.css, at the ink height and stroke of the
  hand-drawn window buttons;
- top bar: icon size such that the ink of the status icons lands on the cap height of the clock.
Icons are rendered at 10 times their displayed size; tolerances are in displayed px.

Usage: check_ink_grid.py [--icons DIR]   (uv runs it with fontTools; needs rsvg-convert, ffmpeg and Google Sans Flex)
Exit status 1 when a measure is off the grid, 2 when a size cannot be read.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ink_grid as grid           # noqa: E402
import map as status_map          # noqa: E402

ZOOM = 10
INK_TOLERANCE, STROKE_TOLERANCE = 1.0, 0.25    # displayed px


def alpha(svg, size):
    n = round(size * ZOOM)
    png = subprocess.run(['rsvg-convert', '-w', str(n), '-h', str(n), str(svg)], capture_output=True, check=True).stdout
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', '-', '-f', 'rawvideo', '-pix_fmt', 'gray8',
                          '-vf', 'alphaextract', '-'], input=png, capture_output=True, check=True).stdout
    return [raw[i * n:(i + 1) * n] for i in range(n)]


def ink(svg, size):
    """Ink height (displayed px)."""
    rows = [i for i, r in enumerate(alpha(svg, size)) if max(r) > 127]
    return (rows[-1] - rows[0] + 1) / ZOOM


def stroke(svg, size):
    """Thickness of the first horizontal stroke met down the middle column (displayed px)."""
    rows = alpha(svg, size)
    column = [r[len(rows) // 2] > 127 for r in rows]
    start = column.index(True)
    return column[start:].index(False) / ZOOM


class Report:
    def __init__(self):
        self.failures = []

    def compare(self, name, measured, expected, tolerance):
        ok = abs(measured - expected) <= tolerance
        print(f'{"OK  " if ok else "FAIL"} {name}: {measured:.2f} px (expected {expected:.2f} ± {tolerance})')
        if not ok:
            self.failures.append(name)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--icons', type=Path, default=grid.REPO / 'theme' / 'icons' / 'Material-Symbols' / 'symbolic')
    theme = ap.parse_args().icons
    try:
        t = grid.targets(grid.cap_height(grid.font_file()), grid.shell_css(), grid.gtk4_css())
    except LookupError as e:
        print(f'check_ink_grid.py: {e}', file=sys.stderr)
        return 2
    r = Report()

    # Header bars, at the size set in the GTK 4 sheet, against "maximize" and "minimize" (16 px). Application icons
    # keep the Material proportions from one symbol to the next: only square symbols match the height of "maximize",
    # which equals the cap height of the body text.
    act = theme / 'actions'
    ref_ink = ink(act / 'window-maximize-symbolic.svg', 16)
    ref_stroke = stroke(act / 'window-minimize-symbolic.svg', 16)
    r.compare('ink window-maximize', ref_ink, t['header_ink'], INK_TOLERANCE)
    for n in ('view-grid', 'window-new'):
        r.compare(f'ink {n}', ink(act / f'{n}-symbolic.svg', t['header_icon']), ref_ink, INK_TOLERANCE)
    for n in ('open-menu', 'view-list'):
        r.compare(f'stroke {n}', stroke(act / f'{n}-symbolic.svg', t['header_icon']), ref_stroke, STROKE_TOLERANCE)

    # Top bar: icon size set in the Shell sheet, then the ink of each icon (at that size) against the cap height of
    # the clock, except symbols shrunk by their width, levels framed on their family's complete symbol, and battery.
    r.compare('top-bar icon-size', t['bar_icon'], t['bar_icon_expected'], 0.5)
    for name, v in sorted(status_map.M.items()):
        if v.startswith('!battery_android') or v in status_map.FAMILY:
            continue
        svg = theme / 'status' / f'{name}.svg'
        width = float(re.search(r'data-ink-width="([\d.]+)"', svg.read_text(encoding='utf-8')).group(1))
        if width > 0.99:
            continue
        r.compare(f'top bar {name}', ink(svg, t['bar_icon']), t['bar_ink'], INK_TOLERANCE)

    print(f'{len(r.failures)} off the grid' + (f': {", ".join(r.failures)}' if r.failures else ''))
    return 1 if r.failures else 0


if __name__ == '__main__':
    sys.exit(main())
