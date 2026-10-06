"""Measurement of one captured cell: size, per-corner radius, outline width, background, text and dominant colours."""
from collections import Counter
from dataclasses import dataclass

from pixels import (coverage_map, dist, largest_component, mirror, on_segment, outside, region, subpixel_edge,
                    top_left_radius)

BACKGROUND_THRESHOLD = 6   # max per-channel difference for "colour of the background"
TEXT_CONTRAST = 16         # min per-channel difference from the container for a pixel to be text
# A row whose container is tinted barely above its surroundings (Pixel tiles: surfaceEffect1 over the panel, 5 per
# channel in dark mode) passes a smaller `threshold` (Row.measure): the captures are lossless renders, so a 2-level
# difference is a real colour, not noise. Likewise `text_contrast` for a label drawn at 30 % opacity.


@dataclass
class Measurements:
    height: float
    width: float
    radius: list      # [top-left, top-right, bottom-right, bottom-left]
    stroke: float
    background: tuple
    text: tuple
    dominant: tuple = None   # most frequent non-background colour (label and indicator of a tab, etc.)


def _edges(cmap, x0, x1, y0, y1):
    """(top, bottom, left, right) edges in px, sub-pixel, along the central column and row of the component."""
    h, w = len(cmap), len(cmap[0])
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    column = [cmap[y][cx] for y in range(h)]
    row = cmap[cy]
    has_column, has_row = any(c >= 0.5 for c in column), any(c >= 0.5 for c in row)
    top = subpixel_edge(column, next(y for y in range(h) if column[y] >= 0.5)) if has_column else y0
    bottom = h - subpixel_edge(column[::-1], next(y for y in range(h) if column[::-1][y] >= 0.5)) \
        if has_column else y1 + 1
    left = subpixel_edge(row, next(x for x in range(w) if row[x] >= 0.5)) if has_row else x0
    right = w - subpixel_edge(row[::-1], next(x for x in range(w) if row[::-1][x] >= 0.5)) if has_row else x1 + 1
    return top, bottom, left, right


def _stroke_width(px, interior, x0, cx, cy, cell_rgb):
    """Width of the outline on the left of the central row (0 if the container has no outline)."""
    border = max((px[cy][x] for x in range(x0, min(x0 + 4, cx + 1))), key=lambda p: dist(p, interior),
                 default=interior)
    stroke = 0.0
    if dist(border, interior) > 10 and not on_segment(border, cell_rgb, interior):
        v = [b - i for b, i in zip(border, interior)]
        n2 = sum(x * x for x in v)
        started = False
        for x in range(x0, cx):
            d = [p - i for p, i in zip(px[cy][x], interior)]
            beta = max(0.0, min(1.0, sum(a * b for a, b in zip(d, v)) / n2))
            if beta < 0.1 and started:
                break
            started = started or beta >= 0.5
            stroke += beta
    return stroke


def measure_cell(pb, rect, cell_rgb, threshold=BACKGROUND_THRESHOLD, text_contrast=TEXT_CONTRAST):
    px = region(pb, rect)
    mask = [p for r in px for p in r if dist(p, cell_rgb) > threshold]
    if not mask:
        return Measurements(0, 0, [0, 0, 0, 0], 0, tuple(cell_rgb), tuple(cell_rgb), tuple(cell_rgb))
    background = Counter(mask).most_common(1)[0][0]
    dominant = background
    cmap = coverage_map(px, cell_rgb, background)
    comp = largest_component(cmap)
    if not comp:
        return Measurements(0, 0, [0, 0, 0, 0], 0, background, background, dominant)
    keep = set(comp)
    h, w = len(cmap), len(cmap[0])
    cmap = [[cmap[y][x] if (x, y) in keep or cmap[y][x] < 0.5 else 0.0 for x in range(w)] for y in range(h)]
    xs, ys = [x for x, _ in comp], [y for _, y in comp]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    top, bottom, left, right = _edges(cmap, x0, x1, y0, y1)

    radii = []
    for hz, vt in ((False, False), (True, False), (True, True), (False, True)):
        c = mirror(cmap, hz, vt)
        a0, a1 = (w - 1 - x1, w - 1 - x0) if hz else (x0, x1)
        b0, b1 = (h - 1 - y1, h - 1 - y0) if vt else (y0, y1)
        radii.append(round(top_left_radius(c, a0, a1, b0, b1), 2))

    # Interior = dominant colour of the central quarter (the exact centre often falls on the text).
    qx, qy = (x1 - x0) // 4, (y1 - y0) // 4
    interior = Counter(px[y][x] for y in range(y0 + qy, y1 - qy + 1)
                       for x in range(x0 + qx, x1 - qx + 1)).most_common(1)[0][0]
    stroke = _stroke_width(px, interior, x0, cx, cy, cell_rgb)

    if len(comp) < 0.5 * sum(a >= 0.5 for r in coverage_map(px, cell_rgb, background) for a in r):
        # No container (flat button at rest): several separate glyphs of the same colour, this is text.
        return Measurements(round(bottom - top, 2), round(right - left, 2), radii, 0.0, tuple(cell_rgb), background,
                            dominant)
    # Text = interior pixels: neither reachable from the border of the area without crossing the container
    # (outside), nor neighbours of the outside (anti-aliased edge of the container).
    out = outside(cmap)
    # "Cell background" pixels (outside or hole of the container): a background/container mix touching them is an
    # anti-aliased edge, not text.
    visible_bg = {(x, y) for y in range(max(0, y0 - 1), min(h, y1 + 2)) for x in range(max(0, x0 - 1), min(w, x1 + 2))
                  if dist(px[y][x], cell_rgb) <= threshold}

    area = (x1 - x0 + 1) * (y1 - y0 + 1)
    solid = sum(dist(px[y][x], background) <= 8 for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)) >= 0.5 * area

    def edge_aa(x, y):
        # Solid container: a mix is an edge only if it touches the visible background (otherwise it is dark text on
        # a light background). Outline or icon: any background/container mix is an edge.
        return on_segment(px[y][x], cell_rgb, background) and (not solid or any(
            (x + dx, y + dy) in visible_bg for dx in (-1, 0, 1) for dy in (-1, 0, 1)))
    candidates = [px[y][x] for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)
                  if (x, y) not in out and dist(px[y][x], background) > text_contrast and dist(px[y][x], cell_rgb) > threshold
                  and not any((x + dx, y + dy) in out for dx in (-1, 0, 1) for dy in (-1, 0, 1))
                  and not edge_aa(x, y)]
    # Glyph core: the pixels farthest from the background (GTK 3 sub-pixel smoothing gives coloured fringes more
    # numerous than the core, but less contrasted).
    dmax = max((dist(p, background) for p in candidates), default=0)
    texts = Counter(p for p in candidates if dist(p, background) >= 0.9 * dmax).most_common(1)
    text = texts[0][0] if texts and texts[0][1] >= 6 else background
    return Measurements(round(bottom - top, 2), round(right - left, 2), radii, round(stroke, 2), background, text,
                        dominant)
