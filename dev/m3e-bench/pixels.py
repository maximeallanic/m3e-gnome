"""Image primitives of the measurement: pixel regions, coverage maps, connected components, sub-pixel edges,
corner-radius fit. Pure functions over lists of RGB tuples (apart from `load` and `region`, which read a GdkPixbuf)."""
import math
from collections import Counter, deque

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf  # noqa: E402


def load(path):
    return GdkPixbuf.Pixbuf.new_from_file(str(path))


def rect_in_image(pb, rect):
    x, y, w, h = rect
    return x >= 0 and y >= 0 and x + w <= pb.get_width() and y + h <= pb.get_height()


def region(pb, rect):
    """Rows of RGB tuples of `rect` (clipped to the image)."""
    x, y, w, h = rect
    x, y = max(0, x), max(0, y)
    w, h = min(w, pb.get_width() - x), min(h, pb.get_height() - y)
    data, rs, nc = pb.read_pixel_bytes().get_data(), pb.get_rowstride(), pb.get_n_channels()
    return [[tuple(data[(y + j) * rs + (x + i) * nc:(y + j) * rs + (x + i) * nc + 3]) for i in range(w)]
            for j in range(h)]


def dist(p, q):
    """Largest per-channel difference."""
    return max(abs(a - b) for a, b in zip(p, q))


def majority_edge(px):
    """Most frequent colour on the border of the region (the background of the cell)."""
    edge = px[0] + px[-1] + [r[0] for r in px] + [r[-1] for r in px]
    return Counter(edge).most_common(1)[0][0]


def coverage_map(px, background, color):
    """Coverage (0..1) of `color` laid on `background`, 0 if the pixel is not on this segment."""
    v = [c - f for c, f in zip(color, background)]
    n2 = sum(x * x for x in v) or 1
    nf2 = sum(x * x for x in background) or 1
    out = []
    for row in px:
        line = []
        for p in row:
            d = [c - f for c, f in zip(p, background)]
            a = sum(x * y for x, y in zip(d, v)) / n2
            residue = max(abs(dd - a * vv) for dd, vv in zip(d, v))
            # Drop shadow = darkened background (p ~ k x background, neutral); an anti-aliased edge is a
            # background/container mix (tinted). In light mode the shadow lies on the container path: recognised here.
            k = sum(x * y for x, y in zip(p, background)) / nf2
            shadow = k < 0.995 and max(abs(c - k * f) for c, f in zip(p, background)) < residue
            line.append(min(1.0, max(0.0, a)) if residue < 24 and not shadow else 0.0)
        out.append(line)
    return out


def on_segment(p, a, b, tol=12):
    """Is p a mix of a and b (anti-aliased edge between two flat areas)?"""
    v = [y - x for x, y in zip(a, b)]
    n2 = sum(x * x for x in v) or 1
    d = [y - x for x, y in zip(a, p)]
    t = max(0.0, min(1.0, sum(x * y for x, y in zip(d, v)) / n2))
    return max(abs(dd - t * vv) for dd, vv in zip(d, v)) < tol


def largest_component(cmap):
    h, w = len(cmap), len(cmap[0])
    seen, best = set(), []
    for j in range(h):
        for i in range(w):
            if cmap[j][i] >= 0.5 and (i, j) not in seen:
                comp, queue = [], deque([(i, j)])
                seen.add((i, j))
                while queue:
                    x, y = queue.popleft()
                    comp.append((x, y))
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1),
                                   (x + 1, y + 1), (x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1)):
                        if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and cmap[ny][nx] >= 0.5:
                            seen.add((nx, ny))
                            queue.append((nx, ny))
                if len(comp) > len(best):
                    best = comp
    return best


def outside(cmap):
    """Pixels outside the container connected to the border of the area (flood fill from the perimeter)."""
    h, w = len(cmap), len(cmap[0])
    seen = set()
    queue = deque((x, y) for y in range(h) for x in range(w)
                  if (x in (0, w - 1) or y in (0, h - 1)) and cmap[y][x] < 0.5)
    seen.update(queue)
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and cmap[ny][nx] < 0.5:
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


def subpixel_edge(values, i):
    """Position (in px, whole-pixel edges) of the left edge of an area starting at pixel i."""
    a = values[i]
    before = values[i - 1] if i > 0 else 0.0
    return i + 1 - a - before


def top_left_radius(cmap, x0, x1, y0, y1):
    """Fit a circular arc on the left edge of the rows of the top-left quarter."""
    left = []
    for y in range(y0, (y0 + y1) // 2 + 1):
        row = cmap[y]
        i = next((x for x in range(x0, x1 + 1) if row[x] >= 0.5), None)
        if i is not None:
            left.append((y + 0.5, subpixel_edge(row, i)))
    top = []
    for x in range(x0, (x0 + x1) // 2 + 1):
        column = [cmap[y][x] for y in range(len(cmap))]
        j = next((y for y in range(y0, y1 + 1) if column[y] >= 0.5), None)
        if j is not None:
            top.append(subpixel_edge(column, j))
    if not left or not top:
        return 0.0
    edge_left, edge_top = min(x for _, x in left), min(top)
    rmax = min(x1 - x0 + 1, y1 - y0 + 1) / 2
    best, err_min = 0.0, float("inf")
    r = 0.0
    while r <= rmax + 1e-9:
        err = 0.0
        for yc, xe in left:
            dy = edge_top + r - yc
            pred = edge_left + r - math.sqrt(r * r - dy * dy) if dy > 0 and r * r - dy * dy > 0 else (
                edge_left + r if dy > 0 else edge_left)
            err += (xe - pred) ** 2
        if err < err_min - 1e-12:
            best, err_min = r, err
        r += 0.1
    return best


def mirror(cmap, horizontal, vertical):
    c = [list(reversed(r)) for r in cmap] if horizontal else [list(r) for r in cmap]
    return list(reversed(c)) if vertical else c
